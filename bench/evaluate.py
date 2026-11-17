"""Evaluates one patch for one task: hidden functional tests + architecture check.

Usage: python bench/evaluate.py <task_id> <patch.diff>     prints JSON

The patch is applied to a fresh copy of the base project. Test harness
directories (tests/, devtools/) are then restored from the base project, so a
patch cannot pass by editing the tests or the local cluster; such edits are
listed in "harness_touched". Existing tests are the base project's tests,
feature tests come from hidden_tests/.

Outcome of a run:
    patch_failed          the patch does not apply to the base project
    not_solved            some existing or feature test fails
    solved_clean          all tests pass, architecture check passes
    solved_violation      all tests pass, architecture check finds violations
    solved_undetermined   all tests pass, architecture check cannot decide
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import archcheck  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIRS = ("tests", "devtools")
_DIFF_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)


def touched_files(patch_text):
    files = set()
    for old, new in _DIFF_HEADER.findall(patch_text):
        files.update((old, new))
    return sorted(files)


def outcome_of(apply_ok, functional, arch_status):
    if not apply_ok:
        return "patch_failed"
    if not functional:
        return "not_solved"
    return {
        "pass": "solved_clean",
        "violation": "solved_violation",
        "error": "solved_undetermined",
    }[arch_status]


def evaluate(task_dir, patch_text):
    task_dir = Path(task_dir)
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    base = task_dir / "repo"
    files = touched_files(patch_text)
    result = {
        "task": task["id"],
        "files_touched": files,
        "harness_touched": [f for f in files if f.split("/")[0] in HARNESS_DIRS],
        "apply_ok": True,
        "apply_error": None,
    }

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        shutil.copytree(base, workspace, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        if patch_text.strip():
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            patch_file = Path(tmp) / "agent.patch"
            patch_file.write_text(patch_text, encoding="utf-8")
            applied = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(patch_file)],
                cwd=workspace,
                capture_output=True,
                text=True,
            )
            if applied.returncode != 0:
                result.update(apply_ok=False, apply_error=applied.stderr.strip())
                result.update(
                    existing={}, feature={}, functional=False,
                    architecture=None, outcome=outcome_of(False, False, None),
                )
                return result

        for name in HARNESS_DIRS:
            if (workspace / name).exists():
                shutil.rmtree(workspace / name)
            if (base / name).exists():
                shutil.copytree(base / name, workspace / name, ignore=shutil.ignore_patterns("__pycache__"))
        for test in (task_dir / "hidden_tests").glob("*.py"):
            shutil.copy(test, workspace / "tests" / test.name)

        existing, feature = validate.split(validate.run_tests(workspace))
        arch = archcheck.check(workspace, task, base)

    functional = bool(existing) and all(existing.values()) and bool(feature) and all(feature.values())
    result.update(
        existing=existing,
        feature=feature,
        existing_passed=f"{sum(existing.values())}/{len(existing)}",
        feature_passed=f"{sum(feature.values())}/{len(feature)}",
        functional=functional,
        architecture=arch,
        violated_rules=sorted(arch["violations"]),
        outcome=outcome_of(True, functional, arch["status"]),
    )
    return result


def main():
    task_dir = ROOT / "tasks" / sys.argv[1]
    patch_text = Path(sys.argv[2]).read_text(encoding="utf-8")
    print(json.dumps(evaluate(task_dir, patch_text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
