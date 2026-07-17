from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

CHECK_STATUSES = ("roll candidate", "zero baseline", "few candles")
SearchPoint = str
Status = Literal["roll candidate", "zero baseline", "few candles"]


@dataclass(slots=True)
class PriceLabConfig:
    baseline_deep: int
    gap_multiplier: float
    search_points: list[SearchPoint]


@dataclass(slots=True)
class Boundary:
    cur_idx: int
    next_idx: int
    search_point: SearchPoint


@dataclass(slots=True)
class CheckResult:
    roll_datetime: pd.Timestamp
    cur_close: float
    next_open: float
    signed_gap: float
    gap_abs: float
    left_baseline: float | None
    threshold: float | None
    status: Status


@dataclass(slots=True)
class AdjustmentEvent:
    roll_datetime: pd.Timestamp
    signed_gap: float


@dataclass(slots=True)
class SummaryCounts:
    total_boundaries: int
    written_rows: int
    roll_candidate_count: int
    zero_baseline_count: int
    few_candles_count: int
