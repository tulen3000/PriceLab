from __future__ import annotations

from statistics import median

import pandas as pd

from pricelab.models import Boundary, CheckResult, PriceLabConfig, SummaryCounts


def run_check(df: pd.DataFrame, config: PriceLabConfig) -> tuple[list[CheckResult], SummaryCounts]:
    boundaries = build_candidate_boundaries(df=df, search_points=config.search_points)

    results: list[CheckResult] = []
    counts = {"roll candidate": 0, "zero baseline": 0, "few candles": 0}

    for boundary in boundaries:
        result = _check_boundary(df=df, boundary=boundary, config=config)
        if result is None:
            continue
        results.append(result)
        counts[result.status] += 1

    results.sort(key=lambda item: item.roll_datetime)
    summary = SummaryCounts(
        total_boundaries=len(boundaries),
        written_rows=len(results),
        roll_candidate_count=counts["roll candidate"],
        zero_baseline_count=counts["zero baseline"],
        few_candles_count=counts["few candles"],
    )
    return results, summary


def build_candidate_boundaries(df: pd.DataFrame, search_points: list[str]) -> list[Boundary]:
    built: list[Boundary] = []
    seen: set[tuple[int, int]] = set()

    for search_point in search_points:
        if search_point == "day_change":
            items = _build_day_change_boundaries(df)
        elif search_point.startswith("fixed_time = "):
            target_time = search_point.split("=", 1)[1].strip()
            items = _build_fixed_time_boundaries(df, target_time)
        else:
            raise ValueError(f"Unsupported search point: {search_point}")

        for boundary in items:
            key = (boundary.cur_idx, boundary.next_idx)
            if key in seen:
                continue
            seen.add(key)
            built.append(boundary)

    built.sort(key=lambda item: pd.Timestamp(df.at[item.next_idx, "dt"]), reverse=True)
    return built


def _build_day_change_boundaries(df: pd.DataFrame) -> list[Boundary]:
    days = df["trading_date"].drop_duplicates().tolist()
    day_to_indices = _build_day_index_map(df)
    boundaries: list[Boundary] = []
    for position in range(len(days) - 1):
        current_day = pd.Timestamp(days[position])
        next_day = pd.Timestamp(days[position + 1])
        boundaries.append(
            Boundary(
                cur_idx=day_to_indices[current_day][-1],
                next_idx=day_to_indices[next_day][0],
                search_point="day_change",
            )
        )
    return boundaries


def _build_fixed_time_boundaries(df: pd.DataFrame, target_time: str) -> list[Boundary]:
    boundaries: list[Boundary] = []
    time_text = df["dt"].dt.strftime("%H:%M")
    for cur_idx, current_time in enumerate(time_text):
        if current_time != target_time:
            continue
        next_idx = cur_idx + 1
        if next_idx >= len(df):
            continue
        boundaries.append(
            Boundary(cur_idx=cur_idx, next_idx=next_idx, search_point=f"fixed_time = {target_time}")
        )
    return boundaries


def _build_day_index_map(df: pd.DataFrame) -> dict[pd.Timestamp, list[int]]:
    mapping: dict[pd.Timestamp, list[int]] = {}
    for idx, day in enumerate(df["trading_date"]):
        mapping.setdefault(pd.Timestamp(day), []).append(idx)
    return mapping


def _check_boundary(df: pd.DataFrame, boundary: Boundary, config: PriceLabConfig) -> CheckResult | None:
    cur_idx = boundary.cur_idx
    next_idx = boundary.next_idx
    cur_close = float(df.at[cur_idx, "<CLOSE>"])
    next_open = float(df.at[next_idx, "<OPEN>"])
    signed_gap = next_open - cur_close
    gap_abs = abs(signed_gap)
    roll_datetime = pd.Timestamp(df.at[next_idx, "dt"])

    base_deltas = _collect_left_deltas(df=df, cur_idx=cur_idx, bars_left=config.baseline_deep)
    if base_deltas is None:
        return CheckResult(
            roll_datetime=roll_datetime,
            cur_close=cur_close,
            next_open=next_open,
            signed_gap=signed_gap,
            gap_abs=gap_abs,
            left_baseline=None,
            threshold=None,
            status="few candles",
        )

    baseline = _baseline_from_deltas(base_deltas)
    if baseline is None:
        return CheckResult(
            roll_datetime=roll_datetime,
            cur_close=cur_close,
            next_open=next_open,
            signed_gap=signed_gap,
            gap_abs=gap_abs,
            left_baseline=0.0,
            threshold=0.0,
            status="zero baseline",
        )

    threshold = baseline * config.gap_multiplier
    status = "roll candidate" if gap_abs > threshold else None
    if status is None:
        return None
    return CheckResult(
        roll_datetime=roll_datetime,
        cur_close=cur_close,
        next_open=next_open,
        signed_gap=signed_gap,
        gap_abs=gap_abs,
        left_baseline=baseline,
        threshold=threshold,
        status="roll candidate",
    )


def _collect_left_deltas(df: pd.DataFrame, cur_idx: int, bars_left: int) -> list[float] | None:
    if bars_left <= 0:
        raise ValueError("bars_left must be > 0")
    # Eligible transitions are on the left side of the boundary and include the transition that ends at cur_bar.
    # The boundary transition cur_bar -> next_bar is excluded.
    last_transition_end = cur_idx
    first_transition_end = last_transition_end - bars_left + 1
    if first_transition_end < 1:
        return None

    deltas: list[float] = []
    for end_idx in range(first_transition_end, last_transition_end + 1):
        prev_close = float(df.at[end_idx - 1, "<CLOSE>"])
        current_open = float(df.at[end_idx, "<OPEN>"])
        deltas.append(abs(current_open - prev_close))
    return deltas


def _baseline_from_deltas(deltas: list[float] | None) -> float | None:
    if not deltas:
        return None
    median_value = float(median(deltas))
    if median_value > 0:
        return median_value
    max_value = float(max(deltas))
    if max_value > 0:
        return max_value
    return None
