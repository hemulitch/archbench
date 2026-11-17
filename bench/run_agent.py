"""Runs a coding agent on benchmark tasks and stores everything needed to recompute results.

    python bench/run_agent.py --tasks t1_acl_delivery --models claude-haiku-5-5 \
        --conditions adr_in_repo --repeats 1

Each run gets its own directory runs/<run_id>/:
    config.json        what was run: task, model, condition, prompt hash, versions, commit
    prompt.md          the exact prompt given to the agent
    transcript.jsonl   the agent's full event stream
    agent_stderr.log   anything the agent printed to stderr
    agent.json         summary of the agent session: turns, cost, tool calls, denials
    patch.diff         the agent's change against the base project
    eval.json          hidden tests + architecture check of patch.diff (bench/evaluate.py)

Metrics are computed from patch.diff only, so a run can be re-evaluated without
calling the model again: python bench/evaluate.py <task> runs/<id>/patch.diff

The agent sees a copy of repo/ in a temporary directory outside the benchmark,
never hidden_tests/, arch/, solutions/ or task.yaml.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "bench" / "prompts"
RUNS = ROOT / "runs"
VENV_BIN = ROOT / ".venv" / "bin"

# How the rules reach the agent.
CONDITIONS = {
    "no_adr": "docs/adr/ removed from the project, rules not mentioned",
    "adr_in_repo": "project as is: rules in docs/adr/, the agent may find them itself",
    "adr_in_prompt": "project as is, plus the text of docs/adr/ in the prompt",
}

# --- agent: Claude Code in headless mode ------------------------------------

CLAUDE_TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
# Shell commands the agent may run without asking; anything else is denied.
CLAUDE_ALLOWED_BASH = [
    f"Bash({cmd}:*)"
    for cmd in (
        "python", "python3", "pytest", "ls", "cat", "head", "tail", "wc",
        "grep", "find", "sed", "diff", "git", "mkdir", "touch",
    )
]


def claude_command(model, effort, max_budget_usd):
    return [
        shutil.which("claude") or "claude",
        "-p",
        "--model", model,
        "--effort", effort,
        "--output-format", "stream-json",
        "--verbose",
        # Clean, reproducible agent: no personal settings, memory, plugins, MCP or skills.
        "--safe-mode",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--tools", CLAUDE_TOOLS,
        # Edits inside the workspace are allowed, everything that would prompt is denied.
        "--permission-mode", "acceptEdits",
        "--permission-prompts", "none",
        "--max-budget-usd", str(max_budget_usd),
        "--allowedTools", *CLAUDE_ALLOWED_BASH,
    ]


def agent_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_")}
    env["PATH"] = f"{VENV_BIN}{os.pathsep}{env.get('PATH', '')}"
    env["VIRTUAL_ENV"] = str(VENV_BIN.parent)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


def summarize_transcript(path):
    """Session facts that matter for analysis, taken from the stream-json log."""
    summary = {"tool_calls": {}, "read_adr": False, "read_diagram": False}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            summary["model"] = event.get("model")
            summary["claude_code_version"] = event.get("claude_code_version")
            summary["tools"] = event.get("tools")
        elif kind == "assistant":
            content = event.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                summary["tool_calls"][name] = summary["tool_calls"].get(name, 0) + 1
                text = json.dumps(block.get("input", {}), ensure_ascii=False)
                summary["read_adr"] |= "docs/adr" in text or "/adr/" in text
                summary["read_diagram"] |= "architecture.puml" in text
        elif kind == "result":
            for key in ("subtype", "is_error", "num_turns", "duration_ms", "total_cost_usd",
                        "stop_reason", "terminal_reason", "usage", "permission_denials"):
                summary[key] = event.get(key)
            summary["final_message"] = event.get("result")
    summary.setdefault("subtype", "no_result_event")
    return summary


# --- workspace ----------------------------------------------------------------

def git(workspace, *args, **kwargs):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "archbench", "GIT_AUTHOR_EMAIL": "archbench@localhost",
        "GIT_COMMITTER_NAME": "archbench", "GIT_COMMITTER_EMAIL": "archbench@localhost",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    }
    return subprocess.run(["git", *args], cwd=workspace, env=env, check=True,
                          capture_output=True, text=True, **kwargs)


def make_workspace(task_dir, condition):
    workspace = Path(tempfile.mkdtemp(prefix="archbench-ws-")) / "project"
    shutil.copytree(task_dir / "repo", workspace,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    if condition == "no_adr":
        shutil.rmtree(workspace / "docs" / "adr", ignore_errors=True)
        if not any((workspace / "docs").iterdir()):
            (workspace / "docs").rmdir()
        readme = workspace / "README.md"
        lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
        readme.write_text("".join(l for l in lines if "docs/adr" not in l), encoding="utf-8")
    git(workspace, "init", "-q", "-b", "main")
    # Ignore build noise without adding a visible .gitignore to the project.
    (workspace / ".git" / "info" / "exclude").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf-8")
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "-m", "base")
    return workspace


def agent_patch(workspace):
    git(workspace, "add", "-A")
    return git(workspace, "diff", "--cached", "--binary", "HEAD").stdout


def render_prompt(task_dir, condition):
    issue = (task_dir / "issue.md").read_text(encoding="utf-8").strip()
    rules = ""
    if condition == "adr_in_prompt":
        adrs = "\n\n".join(
            f'<adr file="docs/adr/{path.name}">\n{path.read_text(encoding="utf-8").strip()}\n</adr>'
            for path in sorted((task_dir / "repo" / "docs" / "adr").glob("*.md"))
        )
        rules = (PROMPTS / "rules.md").read_text(encoding="utf-8").replace("{adrs}", adrs)
    template = (PROMPTS / "task.md").read_text(encoding="utf-8")
    return template.replace("{rules}", rules).replace("{issue}", issue)


# --- provenance -------------------------------------------------------------

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree_hash(directory):
    digest = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(directory)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def bench_commit():
    def out(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": out("rev-parse", "HEAD"), "dirty": bool(out("status", "--porcelain"))}


def tool_versions():
    def out(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return None
    aact = json.loads((ROOT / "node_modules" / "aact" / "package.json").read_text())["version"]
    return {
        "claude_code": out([shutil.which("claude") or "claude", "--version"]),
        "python_agent_env": out([str(VENV_BIN / "python"), "--version"]),
        "aact": aact,
    }


# --- one run -----------------------------------------------------------------

def run_id(task_id, agent, model, condition, effort, repeat):
    return f"{task_id}__{agent}__{model}__{condition}__{effort}__r{repeat}"


def run_one(task_id, model, condition, effort, repeat, timeout_s, max_budget_usd, keep_workspace):
    task_dir = ROOT / "tasks" / task_id
    rid = run_id(task_id, "claude-code", model, condition, effort, repeat)
    out = RUNS / rid
    if (out / "eval.json").exists():
        print(f"skip  {rid} (done)")
        return json.loads((out / "eval.json").read_text(encoding="utf-8"))
    if out.exists():
        shutil.rmtree(out)  # an unfinished run is redone from scratch
    out.mkdir(parents=True)

    prompt = render_prompt(task_dir, condition)
    (out / "prompt.md").write_text(prompt, encoding="utf-8")
    command = claude_command(model, effort, max_budget_usd)
    config = {
        "run_id": rid,
        "task": task_id,
        "task_hash": tree_hash(task_dir),
        "agent": "claude-code",
        "model_requested": model,
        "effort": effort,
        "condition": condition,
        "condition_description": CONDITIONS[condition],
        "repeat": repeat,
        "prompt_sha256": sha256_text(prompt),
        "command": command,
        "timeout_s": timeout_s,
        "max_budget_usd": max_budget_usd,
        "bench": bench_commit(),
        "versions": tool_versions(),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    workspace = make_workspace(task_dir, condition)
    print(f"run   {rid}\n      workspace {workspace}", flush=True)
    started = time.monotonic()
    timed_out = False
    with open(out / "transcript.jsonl", "wb") as transcript, open(out / "agent_stderr.log", "wb") as stderr:
        try:
            done = subprocess.run(command, input=prompt.encode("utf-8"), cwd=workspace,
                                  env=agent_env(), stdout=transcript, stderr=stderr, timeout=timeout_s)
            exit_code = done.returncode
        except subprocess.TimeoutExpired:
            timed_out, exit_code = True, None

    agent = summarize_transcript(out / "transcript.jsonl")
    agent.update(exit_code=exit_code, timed_out=timed_out,
                 wall_time_s=round(time.monotonic() - started, 1))
    (out / "agent.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")

    patch = agent_patch(workspace)
    (out / "patch.diff").write_text(patch, encoding="utf-8")
    if keep_workspace:
        print(f"      kept workspace {workspace}")
    else:
        shutil.rmtree(workspace.parent, ignore_errors=True)

    result = evaluate.evaluate(task_dir, patch)
    result["agent_ok"] = exit_code == 0 and not timed_out and not agent.get("is_error")
    (out / "eval.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      {result['outcome']}  tests {result.get('existing_passed')} + {result.get('feature_passed')}"
          f"  rules {result.get('violated_rules')}  turns {agent.get('num_turns')}"
          f"  cost ${agent.get('total_cost_usd') or 0:.3f}  read_adr {agent['read_adr']}"
          f"  {agent['wall_time_s']}s", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", default="all", help="comma-separated task ids or 'all'")
    parser.add_argument("--models", default="claude-haiku-5-5", help="comma-separated model ids")
    parser.add_argument("--conditions", default="adr_in_repo", help=f"comma-separated: {', '.join(CONDITIONS)}")
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per run")
    parser.add_argument("--max-budget-usd", type=float, default=5.0, help="per run")
    parser.add_argument("--keep-workspace", action="store_true")
    args = parser.parse_args()

    all_tasks = sorted(p.name for p in (ROOT / "tasks").iterdir() if (p / "task.yaml").exists())
    tasks = all_tasks if args.tasks == "all" else args.tasks.split(",")
    conditions = args.conditions.split(",")
    for name in tasks:
        if name not in all_tasks:
            parser.error(f"unknown task {name}")
    for name in conditions:
        if name not in CONDITIONS:
            parser.error(f"unknown condition {name}")

    for repeat in range(1, args.repeats + 1):
        for model in args.models.split(","):
            for condition in conditions:
                for task_id in tasks:
                    run_one(task_id, model, condition, args.effort, repeat,
                            args.timeout, args.max_budget_usd, args.keep_workspace)


if __name__ == "__main__":
    main()
