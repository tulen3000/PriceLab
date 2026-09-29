# PriceLab

PriceLab is a command-line utility for detecting roll gaps in continuous
futures data and back-adjusting confirmed rolls. It processes CSV/TSV OHLC time-series exports.

PriceLab does not make the final decision automatically:

1. `check` finds roll candidates at configured search points;
2. the user selects the confirmed roll dates;
3. `adjust` shifts historical OHLC values to remove the confirmed gaps.

See the [English specification](docs/spec.en.md) or the
[full original specification in Russian](docs/spec.ru.md).

## Installation

Python 3.11 or newer is required.

```powershell
python -m pip install -e .
```

The repository owner normally runs PriceLab without installation. VS Code adds
`src` to `PYTHONPATH` through a local `.vscode/settings.json`. Editable
installation is provided as a portable option for repository visitors.

## Usage

```powershell
python -m pricelab check `
  --quotes rates\Si\M1_2026.csv `
  --params rates\params.yaml

python -m pricelab adjust `
  --quotes rates\Si\M1_2026.csv `
  --rolls rates\Si\M1_2026_roll_candidates.csv
```

Example configuration:

```yaml
baselineDeep: 300
gapMultiplier: 100
searchPoints:
  - day_change
  - fixed_time = 13:59
```

`rates/params.yaml` is a working configuration. Its values are tuned for a
particular futures contract and are not used by the tests as a fixed reference.

## Tests

Install the optional development dependency and run pytest:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

`rates/Si/M1_2026.csv` is intentionally included as a real reference dataset
for the complete `check → adjust` test scenario.

## Engineering approach

The project favors correctness, KISS and clarity over architecture for its own
sake. The detailed [code quality agreement](docs/code_quality.md) is currently
maintained in Russian.

## License

PriceLab is released under the [0BSD license](LICENSE).
