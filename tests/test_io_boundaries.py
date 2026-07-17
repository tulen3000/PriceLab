from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pricelab.io import load_params, load_roll_datetimes_only, save_check_results


def test_empty_check_result_is_a_valid_rolls_csv(tmp_path: Path) -> None:
    output = tmp_path / "roll_candidates.csv"

    save_check_results([], output)

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
