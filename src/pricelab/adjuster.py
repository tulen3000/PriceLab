from __future__ import annotations

import pandas as pd

from pricelab.io import PRICE_COLUMNS
from pricelab.models import AdjustmentEvent


def build_adjustment_events(df: pd.DataFrame, roll_datetimes: list[pd.Timestamp]) -> list[AdjustmentEvent]:
    events: list[AdjustmentEvent] = []
    dt_to_idx = {pd.Timestamp(dt): idx for idx, dt in enumerate(df["dt"])}

    for roll_datetime in sorted([pd.Timestamp(x) for x in roll_datetimes], reverse=True):
        if roll_datetime not in dt_to_idx:
            raise ValueError(f"roll_datetime is absent in quotes file: {roll_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        next_idx = dt_to_idx[roll_datetime]
        if next_idx == 0:
            raise ValueError(
                f"roll_datetime has no previous bar in quotes file: {roll_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        cur_idx = next_idx - 1
        signed_gap = float(df.at[next_idx, "<OPEN>"] - df.at[cur_idx, "<CLOSE>"])
        events.append(AdjustmentEvent(roll_datetime=roll_datetime, signed_gap=signed_gap))
    return events


def apply_back_adjustment(df: pd.DataFrame, events: list[AdjustmentEvent]) -> pd.DataFrame:
    adjusted = df.copy()
    dt_to_idx = {pd.Timestamp(dt): idx for idx, dt in enumerate(adjusted["dt"])}
    for event in sorted(events, key=lambda item: item.roll_datetime, reverse=True):
        next_idx = dt_to_idx[event.roll_datetime]
        mask = adjusted.index < next_idx
        adjusted.loc[mask, PRICE_COLUMNS] = adjusted.loc[mask, PRICE_COLUMNS] + event.signed_gap
    return adjusted
