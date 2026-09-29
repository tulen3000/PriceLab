from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pricelab.io import load_params, load_quotes, load_roll_datetimes_only, save_check_results, save_quotes
from pricelab.models import CheckResult


def test_empty_check_result_is_a_valid_rolls_csv(tmp_path: Path) -> None:
    output = tmp_path / "roll_candidates.csv"

    save_check_results([], output, 0, 1)

    saved = pd.read_csv(output)
    assert list(saved.columns) == [
        "roll_datetime",
        "cur_close",
        "next_open",
        "signed_gap",
        "gap_abs",
        "left_baseline",
        "threshold",
        "status",
    ]
    assert saved.empty

    with pytest.raises(ValueError, match="does not contain"):
        load_roll_datetimes_only(output)


def test_output_files_hide_float_noise_and_preserve_quote_format(tmp_path: Path) -> None:
    source = tmp_path / "quotes.csv"
    rolled = tmp_path / "rolled.csv"
    candidates = tmp_path / "candidates.csv"
    source.write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2026.06.17\t09:00:00\t10.749\t10.750\t10.748\t10.749\t22\t615\t1\n",
        encoding="utf-8",
    )

    quotes = load_quotes(source)
    quotes.loc[0, ["<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]] += 0.2909999999999986
    save_quotes(quotes, rolled)
    save_check_results(
        [
            CheckResult(
                pd.Timestamp("2026-06-17 09:00:00"),
                10.749,
                11.04,
                0.2909999999999986,
                0.2909999999999986,
                0.0004999999999997229,
                0.009999999999994458,
                "roll candidate",
            )
        ],
        candidates,
        int(quotes.attrs["price_digits"]),
        20,
    )

    assert rolled.read_text(encoding="utf-8").splitlines()[1] == (
        "2026.06.17\t09:00:00\t11.040\t11.041\t11.039\t11.040\t22\t615\t1"
    )
    assert candidates.read_text(encoding="utf-8").splitlines()[1] == (
        "2026-06-17 09:00:00,10.749,11.04,0.291,0.291,0.0005,0.01,roll candidate"
    )


@pytest.mark.parametrize("fixed_time", ["24:00", "13:60", "9:00", "noon"])
def test_params_reject_invalid_fixed_time(tmp_path: Path, fixed_time: str) -> None:
    params = tmp_path / "params.yaml"
    params.write_text(
        "\n".join(
            [
                "baselineDeep: 300",
                "gapMultiplier: 100",
                "searchPoints:",
                f"  - fixed_time = {fixed_time}",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported search point"):
        load_params(params)
