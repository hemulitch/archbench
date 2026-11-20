/**
 * Custom rule written against AACT's RuleDefinition shape (see AACT's
 * examples/custom-rules): an element of one bounded context may depend on
 * another bounded context only through that context's contract module.
 */
export const bcIsolationRule = {
  name: "bcIsolation",
  description: "Cross-module dependencies must target the module's contract",
  check(model: any, options?: { bcTagPrefix?: string; contractSuffix?: string }) {
    const prefix = options?.bcTagPrefix ?? "bc:";
    const suffix = options?.contractSuffix ?? "_contracts";
    const bcOf = (name: string): string | undefined =>
      model.elements[name]?.tags
        .find((tag: string) => tag.startsWith(prefix))
        ?.slice(prefix.length);

    const violations = [];
    for (const element of Object.values<any>(model.elements)) {
      const sourceBc = bcOf(element.name);
      if (!sourceBc) continue;
      for (const relation of element.relations) {
        const targetBc = bcOf(relation.to);
        if (!targetBc || targetBc === sourceBc) continue;
        if (relation.to.endsWith(suffix)) continue;
        violations.push({
          target: element.name,
          targetKind: "element",
          message: `${element.name} (${sourceBc}) reaches ${relation.to} (${targetBc}) past its contract`,
        });
      }
    }
    return violations;
  },
};
