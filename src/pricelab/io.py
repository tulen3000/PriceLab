from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from pricelab.models import CheckResult, PriceLabConfig

EXPECTED_COLUMNS = ["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]
PRICE_COLUMNS = ["<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]
SERVICE_COLUMNS = {"dt", "trading_date"}


def load_quotes(quotes_path: Path) -> pd.DataFrame:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Quotes file not found: {quotes_path}")
    try:
        df = pd.read_csv(quotes_path, sep=None, engine="python")
    except Exception as exc:
        raise ValueError(f"Cannot read quotes file: {quotes_path}") from exc

    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Quotes file is missing required columns: {missing}")

    result = df.copy()
    result["dt"] = pd.to_datetime(result["<DATE>"] + " " + result["<TIME>"], format="%Y.%m.%d %H:%M:%S", errors="raise")
    result["trading_date"] = pd.to_datetime(result["<DATE>"], format="%Y.%m.%d", errors="raise")
    for col in PRICE_COLUMNS:
        result[col] = pd.to_numeric(result[col], errors="raise")
    if result["dt"].duplicated().any():
        raise ValueError("Quotes file contains duplicate datetime rows")
    if not result["dt"].is_monotonic_increasing:
        raise ValueError("Quotes file must be sorted by datetime ascending")
    return result


def load_params(params_path: Path) -> PriceLabConfig:
    if not params_path.exists():
        raise FileNotFoundError(f"Params file not found: {params_path}")
    suffix = params_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with open(params_path, "r", encoding="utf-8-sig") as f:
            data = yaml.safe_load(f) or {}
    elif suffix == ".env":
        data = _parse_env_file(params_path)
    else:
        raise ValueError("Params file must be .yaml, .yml or .env")

    for key in ("baselineDeep", "gapMultiplier", "searchPoints"):
        if key not in data:
            raise ValueError(f"Params file must contain {key}")

    try:
        baseline_deep = int(data["baselineDeep"])
        gap_multiplier = float(data["gapMultiplier"])
    except Exception as exc:
        raise ValueError("baselineDeep and gapMultiplier must be numeric") from exc
    if baseline_deep <= 0:
        raise ValueError("baselineDeep must be > 0")
    if gap_multiplier <= 0:
        raise ValueError("gapMultiplier must be > 0")

    search_points = _normalize_search_points(data["searchPoints"])
    if not search_points:
        raise ValueError("searchPoints must not be empty")
    for point in search_points:
        if point == "day_change":
            continue
        if point.startswith("fixed_time = ") and len(point.split("=", 1)[1].strip()) == 5:
            continue
        raise ValueError(f"Unsupported search point: {point}")

    return PriceLabConfig(
        baseline_deep=baseline_deep,
        gap_multiplier=gap_multiplier,
        search_points=search_points,
    )


def _normalize_search_points(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for chunk in value.split(";") for part in chunk.split(",")]
        return [part for part in parts if part]
    raise ValueError("searchPoints must be a list or string")


def _parse_env_file(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid env line: {raw_line.rstrip()}")
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def save_check_results(results: list[CheckResult], output_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for item in results:
        rows.append(
            {
                "roll_datetime": item.roll_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "cur_close": _maybe_int(item.cur_close),
                "next_open": _maybe_int(item.next_open),
                "signed_gap": _maybe_int(item.signed_gap),
                "gap_abs": _maybe_int(item.gap_abs),
                "left_baseline": _maybe_int(item.left_baseline),
                "threshold": _maybe_int(item.threshold),
                "status": item.status,
            }
        )
    pd.DataFrame(rows).to_csv(output_path, index=False)


def load_roll_datetimes_only(rolls_path: Path) -> list[pd.Timestamp]:
    if not rolls_path.exists():
        raise FileNotFoundError(f"Rolls file not found: {rolls_path}")
    suffix = rolls_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(rolls_path)
        if "roll_datetime" not in df.columns:
            raise ValueError("Rolls file must contain roll_datetime column")
        values = df["roll_datetime"].dropna().tolist()
    else:
        values = list(_iter_non_empty_lines(rolls_path))
    if not values:
        raise ValueError("Rolls file does not contain roll_datetime values")

    datetimes = [pd.to_datetime(value) for value in values]
    duplicates = sorted({d for d in datetimes if datetimes.count(d) > 1})
    if duplicates:
        dupes = ", ".join(d.strftime("%Y-%m-%d %H:%M:%S") for d in duplicates)
        raise ValueError(f"Duplicate roll_datetime found: {dupes}")
    return datetimes


def _iter_non_empty_lines(path: Path) -> Iterable[str]:
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line:
                yield line


def save_quotes(df: pd.DataFrame, output_path: Path) -> None:
    export_columns = [column for column in df.columns if column not in SERVICE_COLUMNS]
    df[export_columns].to_csv(output_path, sep="\t", index=False)


def default_check_output_path(quotes_path: Path) -> Path:
    return quotes_path.with_name(f"{quotes_path.stem}_roll_candidates.csv")


def default_adjust_output_path(quotes_path: Path) -> Path:
    return quotes_path.with_name(f"{quotes_path.stem}_rolled{quotes_path.suffix}")


def _maybe_int(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    value = float(value)
    if value.is_integer():
        return int(round(value))
    return value
