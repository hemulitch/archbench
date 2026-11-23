"""Architecture check for one workspace. Usage: archcheck.py <workspace> <task.yaml>

Prints JSON and exits 0 (conformant), 1 (violations) or 2 (could not decide).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import extract  # noqa: E402

BENCH = Path(__file__).resolve().parent


def run_aact(payload):
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        local = BENCH.parent / "node_modules" / ".bin" / "tsx"
        tsx = str(local) if local.exists() else shutil.which("tsx") or "tsx"
        done = subprocess.run(
            [tsx, str(BENCH / "aact_runner.ts"), str(input_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=BENCH,
        )
    if done.returncode != 0:
        raise RuntimeError(f"aact runner failed:\n{done.stderr}")
    return json.loads(done.stdout)


def changed_roles(elements, base_root):
    """A service must not change its architectural role to silence a rule."""
    base_elements, _ = extract.config_model(base_root)
    base_tags = {element["name"]: set(element["tags"]) for element in base_elements}
    return [
        f"{element['name']}: architecture tags changed from {sorted(base_tags[element['name']])}"
        f" to {sorted(element['tags'])}"
        for element in elements
        if element["name"] in base_tags and set(element["tags"]) != base_tags[element["name"]]
    ]


def check_scenario(workspace, arch, base_root):
    """Run a benchmark-owned scenario that returns a JSON list of violations."""
    try:
        scenario = (Path(base_root).parent / "arch" / "check.py").resolve(strict=True)
        done = subprocess.run(
            [sys.executable, "-I", str(scenario), str(workspace.resolve())],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if done.returncode:
            detail = done.stderr.strip().splitlines()
            raise RuntimeError(detail[-1] if detail else f"exit code {done.returncode}")
        messages = json.loads(done.stdout)
        if not isinstance(messages, list) or any(
            not isinstance(message, str) or not message.strip() for message in messages
        ):
            raise ValueError("expected a JSON list of nonempty violation messages")
    except (OSError, TypeError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        return {"status": "error", "violations": {}, "issues": [f"scenario: {error}"]}

    violations = {
        arch["rule"]: [{"target": arch["target"], "message": message} for message in messages]
    } if messages else {}
    return {"status": "violation" if violations else "pass", "violations": violations, "issues": []}


def check(workspace, task, base_root=None):
    arch = task["architecture"]
    workspace = Path(workspace)
    if arch["source"] == "scenario":
        return check_scenario(workspace, arch, base_root)
    if arch["source"] == "config":
        elements, issues = extract.config_model(workspace)
        if base_root:
            issues += changed_roles(elements, base_root)
    elif arch["source"] == "imports":
        elements, issues = extract.import_model(
            workspace, arch["package"], arch.get("shared_modules", ())
        )
    else:
        raise ValueError(f"unknown source {arch['source']}")

    payload = {"model": {"elements": elements}, "rules": arch["rules"]}
    if arch.get("drift"):
        intended, puml_issues = extract.puml_model(workspace / arch["drift"]["intended"])
        issues += puml_issues
        payload["intended"] = {"elements": intended}

    outcome = run_aact(payload)
    issues += [str(item) for item in outcome["issues"]]
    violations = {name: found for name, found in outcome["violations"].items() if found}
    if outcome["drift"]:
        violations["drift"] = [
            {
                "target": change.get("name") or f"{change.get('from')}->{change.get('to')}",
                "message": f"{change['entity']} {change['action']}",
            }
            for change in outcome["drift"]
        ]
    status = "error" if issues else "violation" if violations else "pass"
    return {"status": status, "violations": violations, "issues": issues}


def main():
    task_path = Path(sys.argv[2])
    task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    result = check(sys.argv[1], task, task_path.parent / "repo")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit({"pass": 0, "violation": 1, "error": 2}[result["status"]])


if __name__ == "__main__":
    main()
