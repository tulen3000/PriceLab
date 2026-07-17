from __future__ import annotations

from pricelab.models import AdjustmentEvent, SummaryCounts


def build_check_summary(summary: SummaryCounts, output_path: str) -> str:
    return "\n".join(
        [
            f"boundaries_checked={summary.total_boundaries}",
            f"rows_written={summary.written_rows}",
            f"roll_candidate={summary.roll_candidate_count}",
            f"zero_baseline={summary.zero_baseline_count}",
            f"few_candles={summary.few_candles_count}",
            f"output={output_path}",
        ]
    )


def build_adjust_summary(events: list[AdjustmentEvent], output_path: str) -> str:
    lines = [f"processed_roll_datetime={len(events)}"]
    for event in sorted(events, key=lambda item: item.roll_datetime, reverse=True):
        lines.append(f"{event.roll_datetime.strftime('%Y-%m-%d %H:%M:%S')} gap={_fmt_number(event.signed_gap)}")
    lines.append(f"output={output_path}")
    return "\n".join(lines)


def _fmt_number(value: float) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(round(value)))
    return f"{value:.6f}"
