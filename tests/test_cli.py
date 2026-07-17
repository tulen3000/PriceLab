from __future__ import annotations

import sys
from pathlib import Path

from pricelab.cli import main


def test_cli_reports_input_error(monkeypatch, capsys, tmp_path: Path) -> None:
    missing_quotes = tmp_path / "missing.csv"
    params = tmp_path / "params.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        ["pricelab", "check", "--quotes", str(missing_quotes), "--params", str(params)],
    )

    assert main() == 1
    assert capsys.readouterr().err == f"ERROR: Quotes file not found: {missing_quotes}\n"
