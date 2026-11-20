"""Checks that every task behaves as a benchmark item should.

    base       existing tests pass, feature tests fail, architecture passes
    correct    all tests pass, architecture passes
    violating  all tests pass, architecture fails on the target rule only

Usage: python bench/validate.py [task_id ...]
"""
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import archcheck  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ("base", "correct", "violating")


def prepare(task_dir, variant, workspace):
    shutil.copytree(
        task_dir / "repo", workspace, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache")
    )
    if variant != "base":
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        subprocess.run(
            ["git", "apply", str(task_dir / "solutions" / f"{variant}.patch")],
            cwd=workspace,
            check=True,
        )
    for test in (task_dir / "hidden_tests").glob("*.py"):
        shutil.copy(test, Path(workspace) / "tests" / test.name)


def run_tests(workspace):
    report = Path(workspace) / "report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--junitxml={report}"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=600,
    )
    results = {}
    for case in ET.parse(report).getroot().iter("testcase"):
        failed = any(child.tag in {"failure", "error"} for child in case)
        results[f"{case.get('classname').split('.')[-1]}::{case.get('name')}"] = not failed
    return results


def split(results):
    feature = {k: v for k, v in results.items() if k.startswith("test_feature")}
    existing = {k: v for k, v in results.items() if not k.startswith("test_feature")}
    return existing, feature


def targets_of(violations):
    return {item["target"] for item in violations}


def judge(variant, existing, feature, arch, expected):
    problems = []
    if not existing or not all(existing.values()):
        problems.append("existing tests must pass")
    if not feature:
        problems.append("no feature tests were run")
    if variant == "base":
        if any(feature.values()):
            problems.append("feature tests must fail on the base project")
        if arch["status"] != "pass":
            problems.append(f"architecture must pass, got {arch}")
    else:
        if not all(feature.values()):
            problems.append("feature tests must pass")
    if variant == "correct" and arch["status"] != "pass":
        problems.append(f"architecture must pass, got {arch}")
    if variant == "violating":
        target = expected["target_rule"]
        if arch["status"] != "violation":
            problems.append(f"architecture must report a violation, got {arch}")
        if set(arch["violations"]) != {target}:
            problems.append(f"only {target} may fail, got {sorted(arch['violations'])}")
        found = targets_of(arch["violations"].get(target, []))
        if not found or not found <= set(expected["violating_targets"]):
            problems.append(f"unexpected offenders: {sorted(found)}")
    return problems


def model_matches_diagram(task_dir, task):
    """The diagram an agent reads must describe the base project truthfully."""
    if task["architecture"]["source"] != "config":
        return None
    probe = {"architecture": {**task["architecture"], "drift": {"intended": "architecture/architecture.puml"}}}
    return archcheck.check(task_dir / "repo", probe)["status"] == "pass"


def validate(task_dir):
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    outcome = {"id": task["id"], "variants": {}, "diagram_matches_base": model_matches_diagram(task_dir, task)}
    for variant in VARIANTS:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            prepare(task_dir, variant, workspace)
            existing, feature = split(run_tests(workspace))
            arch = archcheck.check(workspace, task, task_dir / "repo")
        problems = judge(variant, existing, feature, arch, task["expected"])
        outcome["variants"][variant] = {
            "existing_passed": f"{sum(existing.values())}/{len(existing)}",
            "feature_passed": f"{sum(feature.values())}/{len(feature)}",
            "failed_tests": [k for k, v in {**existing, **feature}.items() if not v],
            "architecture": arch,
            "problems": problems,
        }
    return outcome


def main():
    selected = sys.argv[1:]
    report = []
    for task_dir in sorted((ROOT / "tasks").iterdir()):
        if task_dir.is_dir() and (not selected or task_dir.name in selected):
            report.append(validate(task_dir))

    print(f"{'task':28} {'variant':10} {'existing':9} {'feature':8} {'architecture':32} verdict")
    ok = True
    for task in report:
        if task["diagram_matches_base"] is False:
            ok = False
            print(f"{task['id']:28} diagram does not match deploy/ in the base project")
        for name, data in task["variants"].items():
            arch = data["architecture"]
            found = ",".join(sorted(arch["violations"])) or arch["status"]
            verdict = "OK" if not data["problems"] else "; ".join(data["problems"])
            ok &= not data["problems"]
            print(f"{task['id']:28} {name:10} {data['existing_passed']:9} {data['feature_passed']:8} {found:32} {verdict}")
    (ROOT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
