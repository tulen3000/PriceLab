from __future__ import annotations

from pathlib import Path

from pricelab.adjuster import apply_back_adjustment, build_adjustment_events
from pricelab.detector import run_check
from pricelab.io import load_params, load_quotes, load_roll_datetimes_only


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_check_day_change_writes_only_problem_rows(tmp_path: Path) -> None:
    quotes = tmp_path / "quotes.csv"
    params = tmp_path / "params.yaml"

    _write_text(
        quotes,
        """
<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>
2025.01.01,10:00:00,100,101,99,100
2025.01.01,10:01:00,101,102,100,101
2025.01.01,10:02:00,102,103,101,102
2025.01.02,10:00:00,150,151,149,150
2025.01.02,10:01:00,150,151,149,150
2025.01.02,10:02:00,150,151,149,150
        """,
    )
    _write_text(
        params,
        """
baselineDeep: 2
gapMultiplier: 2
searchPoints:
  - day_change
        """,
    )

    df = load_quotes(quotes)
    config = load_params(params)
    results, summary = run_check(df, config)

    assert len(results) == 1
    assert results[0].status == "roll candidate"
    assert str(results[0].roll_datetime) == "2025-01-02 10:00:00"
    assert summary.roll_candidate_count == 1
    assert summary.zero_baseline_count == 0
    assert summary.few_candles_count == 0


def test_check_supports_fixed_time(tmp_path: Path) -> None:
    quotes = tmp_path / "quotes.csv"
    params = tmp_path / "params.yaml"

    _write_text(
        quotes,
        """
<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>
2025.01.01,13:57:00,100,100,100,100
2025.01.01,13:58:00,101,101,101,101
2025.01.01,13:59:00,102,102,102,102
2025.01.01,14:00:00,220,220,220,220
2025.01.01,14:01:00,220,220,220,220
        """,
    )
    _write_text(
        params,
        """
baselineDeep: 1
gapMultiplier: 10
searchPoints:
  - fixed_time = 13:59
        """,
    )

    df = load_quotes(quotes)
    config = load_params(params)
    results, _summary = run_check(df, config)

    assert len(results) == 1
    assert results[0].status == "roll candidate"
    assert str(results[0].roll_datetime) == "2025-01-01 14:00:00"


def test_zero_baseline(tmp_path: Path) -> None:
    quotes = tmp_path / "quotes.csv"
    params = tmp_path / "params.yaml"

    _write_text(
        quotes,
        """
<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>
2025.01.01,10:00:00,100,100,100,100
2025.01.01,10:01:00,100,100,100,100
2025.01.01,10:02:00,100,100,100,100
2025.01.02,10:00:00,100,100,100,100
        """,
    )
    _write_text(
        params,
        """
baselineDeep: 2
gapMultiplier: 2
searchPoints:
  - day_change
        """,
    )

    df = load_quotes(quotes)
    config = load_params(params)
    results, _summary = run_check(df, config)

    assert len(results) == 1
    assert results[0].status == "zero baseline"


def test_adjust_uses_roll_datetime_and_adjusts_history(tmp_path: Path) -> None:
    quotes = tmp_path / "quotes.csv"
    rolls = tmp_path / "rolls.csv"

    _write_text(
        quotes,
        """
<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>
2025.01.01,13:58:00,100,110,90,101
2025.01.01,13:59:00,102,112,92,103
2025.01.01,14:00:00,150,160,140,151
2025.01.01,14:01:00,151,161,141,152
        """,
    )
    _write_text(
        rolls,
        """
roll_datetime
2025-01-01 14:00:00
        """,
    )

    df = load_quotes(quotes)
    roll_datetimes = load_roll_datetimes_only(rolls)
    events = build_adjustment_events(df, roll_datetimes)
    adjusted = apply_back_adjustment(df, events)

    assert len(events) == 1
    assert events[0].signed_gap == 47
    assert adjusted.loc[0, "<OPEN>"] == 147
    assert adjusted.loc[1, "<CLOSE>"] == 150
    assert adjusted.loc[2, "<OPEN>"] == 150
