"""Aggregates runs/*/ into the benchmark report.

    python bench/report.py                # read runs/*/eval.json
    python bench/report.py --reevaluate   # first recompute eval.json from patch.diff

Metrics, per agent x model x condition x effort (a "setup"):
    M1  functional     share of runs where all existing and feature tests pass
    M2  clean          share of runs that are functional AND have no architecture violations
    M3  violating      among functional runs, share with architecture violations
    U   undetermined   among functional runs, share where the check could not decide
M3 and U are left out of each other: an undetermined run is neither clean nor violating.

Spread: each metric is also computed per repeat (over all tasks of that repeat);
the report shows the mean and the min-max of these per-repeat values.
Writes reports/summary.md and reports/summary.json.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
REPORTS = ROOT / "reports"


def load_runs(reevaluate):
    runs = []
    for run_dir in sorted(RUNS.iterdir()) if RUNS.exists() else []:
        config_path, eval_path = run_dir / "config.json", run_dir / "eval.json"
        if not config_path.exists() or not (eval_path.exists() or reevaluate):
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if reevaluate:
            patch = (run_dir / "patch.diff").read_text(encoding="utf-8")
            result = evaluate.evaluate(ROOT / "tasks" / config["task"], patch)
            old = json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.exists() else {}
            result["agent_ok"] = old.get("agent_ok")
            eval_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"re-evaluated {run_dir.name}: {result['outcome']}", file=sys.stderr)
        agent_path = run_dir / "agent.json"
        runs.append({
            "config": config,
            "eval": json.loads(eval_path.read_text(encoding="utf-8")),
            "agent": json.loads(agent_path.read_text(encoding="utf-8")) if agent_path.exists() else {},
        })
    return runs


def metrics(group):
    n = len(group)
    functional = [r for r in group if r["eval"]["functional"]]
    count = lambda outcome: sum(r["eval"]["outcome"] == outcome for r in group)
    share = lambda part, whole: part / whole if whole else None
    return {
        "runs": n,
        "M1_functional": share(len(functional), n),
        "M2_clean": share(count("solved_clean"), n),
        "M3_violating_among_functional": share(count("solved_violation"), len(functional)),
        "U_undetermined_among_functional": share(count("solved_undetermined"), len(functional)),
        "agent_failures": sum(not r["eval"].get("agent_ok", True) for r in group),
        "read_adr": share(sum(bool(r["agent"].get("read_adr")) for r in group), n),
        "cost_usd": round(sum(r["agent"].get("total_cost_usd") or 0 for r in group), 4),
    }


def spread(group, key):
    by_repeat = defaultdict(list)
    for run in group:
        by_repeat[run["config"]["repeat"]].append(run)
    values = [metrics(runs)[key] for runs in by_repeat.values()]
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {"mean": sum(values) / len(values), "min": min(values), "max": max(values), "repeats": len(values)}


def setup_of(run):
    c = run["config"]
    return (c["agent"], c["model_requested"], c["condition"], c["effort"])


def pct(value):
    return "—" if value is None else f"{100 * value:.0f}%"


def with_spread(sp):
    if sp is None:
        return "—"
    if sp["repeats"] < 2:
        return pct(sp["mean"])
    return f"{pct(sp['mean'])} ({pct(sp['min'])}–{pct(sp['max'])})"


def build(runs):
    setups = defaultdict(list)
    for run in runs:
        setups[setup_of(run)].append(run)

    summary, lines = [], ["# ArchBench: сводка прогонов", ""]
    lines += [
        "M1 — доля функционально решённых; M2 — решено и без нарушений архитектуры;",
        "M3 — доля нарушений среди функционально решённых; U — среди решённых проверка не смогла решить.",
        "В скобках — разброс между повторами (min–max).",
        "",
        "| Агент | Модель | Условие | Effort | Прогонов | M1 | M2 | M3 | U | Читал ADR | Сбои агента | $ |",
        "| --- | --- | --- | --- | --: | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for setup in sorted(setups):
        group = setups[setup]
        m = metrics(group)
        sp = {key: spread(group, key) for key in
              ("M1_functional", "M2_clean", "M3_violating_among_functional", "U_undetermined_among_functional")}
        summary.append({"setup": dict(zip(("agent", "model", "condition", "effort"), setup)),
                        "metrics": m, "spread": sp})
        lines.append(
            f"| {' | '.join(setup)} | {m['runs']} | {with_spread(sp['M1_functional'])}"
            f" | {with_spread(sp['M2_clean'])} | {with_spread(sp['M3_violating_among_functional'])}"
            f" | {with_spread(sp['U_undetermined_among_functional'])} | {pct(m['read_adr'])}"
            f" | {m['agent_failures']} | {m['cost_usd']:.2f} |"
        )

    lines += ["", "## По задачам", "",
              "| Задача | Агент | Модель | Условие | Effort | Исходы | Нарушенные правила |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    by_task = defaultdict(list)
    for run in runs:
        by_task[(run["config"]["task"], *setup_of(run))].append(run)
    for key in sorted(by_task):
        group = sorted(by_task[key], key=lambda r: r["config"]["repeat"])
        outcomes = ", ".join(r["eval"]["outcome"] for r in group)
        rules = sorted({rule for r in group for rule in r["eval"].get("violated_rules") or []})
        lines.append(f"| {' | '.join(key)} | {outcomes} | {', '.join(rules) or '—'} |")
    return summary, "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reevaluate", action="store_true", help="recompute eval.json from patch.diff first")
    args = parser.parse_args()
    runs = load_runs(args.reevaluate)
    summary, markdown = build(runs)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "summary.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
