/**
 * Runs AACT rules (and, when an intended model is given, AACT's diff) over a
 * model extracted from a workspace.
 *
 * Input JSON:  { model, intended?, rules: { <ruleName>: options } }
 * Output JSON: { violations: { <ruleName>: [...] }, drift: [...], issues: [...] }
 *
 * AACT comes from the npm package "aact", or from a source checkout when
 * AACT_SRC points at one.
 */
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { bcIsolationRule } from "./rules/bcIsolation";

const load = async () => {
  const src = process.env.AACT_SRC;
  if (!src) return import("aact" as string);
  const file = (path: string) => import(pathToFileURL(`${src}/src/${path}`).href);
  return { ...(await file("model/index.ts")), ...(await file("rules/index.ts")), ...(await file("diff/index.ts")) };
};

const main = async () => {
  const input = JSON.parse(readFileSync(process.argv[2], "utf8"));
  const aact: any = await load();
  const rules: Record<string, any> = {
    acl: aact.aclRule,
    acyclic: aact.acyclicRule,
    crud: aact.crudRule,
    dbPerService: aact.dbPerServiceRule,
    bcIsolation: bcIsolationRule,
  };
  const build = (raw: any) =>
    aact.buildModel({
      elements: raw.elements,
      boundaries: [],
      rootBoundaryNames: [],
    });
  const built = build(input.model);

  const violations: Record<string, unknown[]> = {};
  for (const [name, options] of Object.entries(input.rules)) {
    if (!rules[name]) throw new Error(`unknown rule: ${name}`);
    violations[name] = rules[name].check(built.model, options);
  }

  let drift: unknown[] = [];
  const issues = [...built.issues];
  if (input.intended) {
    const intended = build(input.intended);
    issues.push(...intended.issues);
    drift = aact
      .computeDiff(
        intended.model,
        built.model,
        { source: "architecture.puml", format: "plantuml" },
        { source: "deploy", format: "model-json" },
      )
      .changes.filter((change: any) => change.severity === "structural");
  }
  process.stdout.write(JSON.stringify({ violations, drift, issues }));
};

main().catch((error) => {
  console.error(error);
  process.exit(2);
});
