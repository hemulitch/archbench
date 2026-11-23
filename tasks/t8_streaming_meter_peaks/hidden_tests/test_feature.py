import pytest

from metering import summary


def sample(watts, tick):
    return {"meter": "A", "tick": tick, "watts": watts}


def test_top_peaks_and_ties_from_a_single_pass():
    records = [sample(watts, tick) for tick, watts in enumerate([3, 20, 5, 20, 20, 100])]
    result = summary.summarize_with_peaks((row for row in records), limit=3)
    assert result == {"count": 6, "total_watts": 168, "peaks": [records[5], records[1], records[3]]}


def test_zero_limit_still_counts_records():
    result = summary.summarize_with_peaks(iter([sample(20, 0)]), limit=0)
    assert result == {"count": 1, "total_watts": 20, "peaks": []}


def test_empty_short_and_invalid_streams():
    assert summary.summarize_with_peaks(iter(())) == {"count": 0, "total_watts": 0, "peaks": []}
    records = [sample(watts, tick) for tick, watts in enumerate([0, 1])]
    assert summary.summarize_with_peaks(iter(records))["peaks"] == records[::-1]
    with pytest.raises(ValueError):
        summary.summarize_with_peaks(iter(records), limit=-1)
