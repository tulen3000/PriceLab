from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

from pricelab.cli import cmd_adjust, cmd_check
from pricelab.io import PRICE_COLUMNS, load_quotes

REAL_QUOTES = Path(__file__).parents[1] / "rates" / "Si" / "M1_2026.csv"

pytestmark = pytest.mark.real_data


def test_si_reference_workflow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    if not REAL_QUOTES.exists():
        pytest.skip(f"Local market data is not available: {REAL_QUOTES}")

    params = tmp_path / "params.yaml"
    candidates = tmp_path / "roll_candidates.csv"
    adjusted_quotes = tmp_path / "M1_2026_rolled.csv"
    params.write_text(
        "\n".join(
            [
                "baselineDeep: 300",
                "gapMultiplier: 100",
                "searchPoints:",
                "  - day_change",
                "  - fixed_time = 13:59",
            ]
        ),
        encoding="utf-8",
    )

    assert cmd_check(Namespace(quotes=str(REAL_QUOTES), params=str(params), output=str(candidates))) == 0
    assert "boundaries_checked=155" in capsys.readouterr().out

    saved_candidates = pd.read_csv(candidates)
    assert list(zip(saved_candidates["roll_datetime"], saved_candidates["signed_gap"], strict=True)) == [
        ("2026-02-24 09:00:00", -154),
        ("2026-03-09 09:00:00", -246),
        ("2026-03-20 09:00:00", 234),
        ("2026-04-13 09:00:00", -249),
        ("2026-04-14 09:00:00", 140),
        ("2026-04-20 09:00:00", -161),
    ]

    assert (
        cmd_adjust(Namespace(quotes=str(REAL_QUOTES), rolls=str(candidates), output=str(adjusted_quotes))) == 0
    )
    assert "processed_roll_datetime=6" in capsys.readouterr().out

    original = load_quotes(REAL_QUOTES)
    adjusted = load_quotes(adjusted_quotes)
    assert adjusted.index.equals(original.index)
    assert adjusted.columns.equals(original.columns)

    unchanged_columns = [column for column in original.columns if column not in PRICE_COLUMNS]
    pd.testing.assert_frame_equal(adjusted[unchanged_columns], original[unchanged_columns])

    for roll_datetime in saved_candidates["roll_datetime"]:
        next_idx = original.index[original["dt"] == pd.Timestamp(roll_datetime)][0]
        assert adjusted.at[next_idx - 1, "<CLOSE>"] == adjusted.at[next_idx, "<OPEN>"]

    assert adjusted.loc[0, PRICE_COLUMNS].tolist() == [82544, 82671, 82544, 82671]
    assert adjusted.loc[len(adjusted) - 1, PRICE_COLUMNS].tolist() == [76014, 76025, 76001, 76025]
