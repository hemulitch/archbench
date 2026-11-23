import json
import sys
import tracemalloc

SMALL = 2_000
LARGE = 60_000
MAX_GROWTH_BYTES = 512 * 1024


def readings(size):
    for tick in range(size):
        yield {"meter": f"line-{tick % 17}", "tick": tick, "watts": (tick * 173) % 18_017}


def peak_allocation(report, size):
    tracemalloc.start()
    try:
        result = report(readings(size))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if result["count"] != size:
        raise ValueError(f"report counted {result['count']} out of {size} records")
    return peak


def check(summary):
    reports = [("summarize", summary.summarize)]
    if callable(getattr(summary, "summarize_with_peaks", None)):
        reports.append(("summarize_with_peaks", lambda rows: summary.summarize_with_peaks(rows, limit=5)))
    violations = []
    for name, report in reports:
        report(readings(20))
        small = peak_allocation(report, SMALL)
        large = peak_allocation(report, LARGE)
        if large - small > MAX_GROWTH_BYTES:
            violations.append(f"{name} peak allocation grew from {small} to {large} bytes "
                              f"with a fixed output limit")
    return violations


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    from metering import summary

    print(json.dumps(check(summary)))
