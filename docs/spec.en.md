# PriceLab — specification

# Scope

PriceLab is a local command-line utility for preparing a continuous futures
series from an MT5 CSV file.

The scope includes:

- detecting roll candidates using the specified algorithm;
- reporting the detected candidates;
- adjusting the series at the selected roll dates;
- saving a new CSV in the MT5 TSV format.

The scope does not include:

- heuristic roll detection or roll scoring;
- automatic confirmation of detected rolls without user involvement;
- working with multiple data providers;
- separate logic for quarterly and monthly futures;
- a machine-readable report.

# Need

MetaTrader 5 is used for trading futures on MOEX.
Futures contracts have an expiration date. When trading moves to a new
contract, its price is usually shifted relative to the previous contract. This
is not a market gap for trading purposes, but broker-provided historical
continuous series often contain this jump as if it were an ordinary price
movement.

During multi-year strategy optimization, such jumps distort the data. A
strategy may begin fitting itself to roll artifacts as though they were market
signals.

I need a program that:

- finds possible rolls in an existing continuous series;
- shows them to the user;
- removes price discontinuities at the selected dates;
- returns a cleaner continuous series for further research.

# Idea

PriceLab is based on the following assumptions:

1. Search points are configured and may be of two types:
   - `day_change`
   - `fixed_time = HH:MM`
2. The difference between the previous candle's close and the next candle's
   open is a typical gap. A typical gap is usually greater than 0 and less than
   10, 20 or 100, depending on the symbol.

For each search point, the program:

- identifies `cur_bar` and `next_bar`;
- calculates the gap between the close of `cur_bar` and the open of `next_bar`;
- compares it with the typical size of recent inter-bar gaps to the left;
- marks the date as a roll candidate if the gap is abnormally large.

PriceLab does not make the final decision. It proposes candidates, and the user
decides which ones to use for adjustment.

# Terms

**search point** — a rule defining where to look for a possible roll.
Supported values:

- `day_change`
- `fixed_time = HH:MM`

**boundary** — a specific pair of adjacent bars, `cur_bar` and `next_bar`,
selected using a search point.

**cur_bar** — the bar after which a possible jump is checked.

**next_bar** — the bar immediately following `cur_bar`, where the jump may
begin.

**signed_gap** — `next_bar.open - cur_bar.close`.

**gap_abs** — `abs(signed_gap)`.

**left_baseline** — the typical absolute inter-bar gap over the configured
number of candles to the left of `cur_bar`.

**roll candidate** — a boundary where an abnormally large gap was found.

**confirmed roll** — a candidate selected by the user for adjustment.

# User stories

## Detection

### US.1 Find roll dates

As a user, I want PriceLab to check the configured roll search points and
identify possible `roll_datetime` values.

### US.2 View candidate parameters

As a user, I want to see the gap and `left_baseline` for every detected date so
that I can decide whether the case resembles a roll.

### US.3 Configure sensitivity

As a user, I want to configure the gap-detection parameters so that I can tune
the detector for a particular instrument and timeframe.

### US.4 Configure roll search points

As a user, I want to specify possible roll search points—a day boundary or a
particular time—so that PriceLab checks the points I selected.

## Adjust

### US.5 Adjust rolls

As a user, I want PriceLab to remove discontinuities using a selected list of
dates so that I obtain a smooth price series.

# Inputs

## Quotes file

An MT5 TSV/CSV file with the following columns:

- `<DATE>`
- `<TIME>`
- `<OPEN>`
- `<HIGH>`
- `<LOW>`
- `<CLOSE>`

Additional columns are allowed. They must not affect the logic and must be
preserved unchanged during adjustment.

## Parameter file

A YAML/ENV file containing:

- `baselineDeep` — the number of candles to the left used to calculate the
  baseline; an integer greater than 0;
- `gapMultiplier` — the multiplier defining how many times the candidate gap
  must exceed `left_baseline`; a number greater than 0;
- `searchPoints` — a list of roll search points.

Supported `searchPoints` values:

- `day_change` — look for a roll at the boundary between the final bar of one
  day and the first bar of the next day;
- `fixed_time = HH:MM` — look for a roll at a boundary where `cur_bar` has the
  specified `HH:MM` time.

# Usage scenarios

## US.1 Find roll dates

1. The user starts the script and specifies the quotes filename.
2. PriceLab checks that the quotes file exists, can be read and has the required
   structure.
3. PriceLab checks that the parameter file exists, contains `baselineDeep` and
   `gapMultiplier`, validates their values and reads the `searchPoints` list.
4. PriceLab opens the quotes file and obtains the candle and price arrays.
5. PriceLab builds a list of candidate boundaries for all search points.
6. PriceLab moves from the most recent boundary to earlier boundaries.

For each search point:

- if the search point is `day_change`:
  - `cur_bar` is the last bar of day `D`;
  - `next_bar` is the first following bar with a date later than `D`;
- if the search point is `fixed_time = HH:MM`:
  - `cur_bar` is the bar with the time `HH:MM`;
  - `next_bar` is the next bar in the quotes file;
- if `cur_bar` and `next_bar` are more than one calendar day apart, they still
  form one boundary when they are adjacent trading sections in the data.

7. Calculate:
   - `signed_gap = next_bar.open - cur_bar.close`
   - `gap_abs = abs(signed_gap)`
8. Take `baselineDeep` inter-bar transitions to the left of `cur_bar`, excluding
   the `cur_bar -> next_bar` transition. If fewer than `baselineDeep` candles
   are available to the left, the boundary receives the `few candles` status.
9. For those candles, calculate:
   - `left_baseline = median(abs(open[i] - close[i-1]))`
10. If `left_baseline` is 0, use:
    - `left_baseline = max(abs(open[i] - close[i-1]))`
11. If the maximum is also 0, the boundary receives the `zero baseline` status.
    The user will see it and inspect the quotes manually.
12. If `gap_abs > left_baseline * gapMultiplier`, the datetime of `next_bar`
    becomes `roll_datetime`. This is the candle where the jump began.
13. When no unprocessed boundaries remain, the file is considered fully
    checked.
14. Create a dates file. For every date, output:
    - `roll_datetime`;
    - `cur_close`;
    - `next_open`;
    - `signed_gap`;
    - `gap_abs`;
    - `left_baseline`;
    - `threshold = left_baseline * gapMultiplier`;
    - status: `roll candidate`, `zero baseline` or `few candles`.

    The dates file in this form must also be suitable as input for `adjust`.
15. Display a console report showing the number of detected dates and the
    number of each status.

## US.3 Configure sensitivity

1. The user opens the configuration file.
2. The user changes the values.
3. PriceLab does not know about or control this action.

## US.5 Adjust rolls

1. The user starts the script and specifies the quotes file and the dates file.
2. PriceLab checks that the quotes file exists, can be read and has the required
   structure.
3. PriceLab checks that the dates file exists and contains `roll_datetime`.
4. PriceLab checks for duplicate dates. If duplicates are present, PriceLab
   warns the user and does not perform adjustment.
5. If the files are valid, processing begins. PriceLab ignores the other data
   and extracts only `roll_datetime`. Other fields from the `check` output do
   not participate in adjustment.
6. Tell the user how many `roll_datetime` values were found.
7. Processing proceeds from the future toward the past while unprocessed
   `roll_datetime` values remain.
8. Take the latest unprocessed date.
9. Calculate `signed_gap = next_bar.open - cur_bar.close`.
10. For every bar with datetime `< roll_datetime`, shift the
    `OPEN/HIGH/LOW/CLOSE` fields:
    - `<OPEN>  := <OPEN>  + signed_gap`
    - `<HIGH>  := <HIGH>  + signed_gap`
    - `<LOW>   := <LOW>   + signed_gap`
    - `<CLOSE> := <CLOSE> + signed_gap`

    Other fields do not change.
11. Mark the `roll_datetime` as processed and take the next one.
12. After each `roll_datetime` is processed, the changes already made are
    retained and participate in subsequent, older adjustments.
13. The processed state of each `roll_datetime` is kept in program memory and
    is not written to a file.
14. Remember which `roll_datetime` values were processed and the size of each
    shift.
15. Write a new CSV with the same structure and in the same MT5 TSV format,
    adding `_rolled` to its name.
16. When processing is complete, display a console report listing the processed
    `roll_datetime` values, their count and the name of the new file.

# Environment requirements

PriceLab is designed for local execution in the user's non-isolated Python
environment.

Requirements:

1. The project runs without requiring a separate virtual environment.
2. The project must support execution from VS Code with the project root open.
3. Local execution in VS Code uses `.vscode/settings.json`, where `PYTHONPATH`
   points to the `src` directory.
4. The package must contain `__main__.py` so that it can be started as:
   `python -m pricelab ...`
5. The project code must be runnable without installing the package into the
   system when `src` is present in `PYTHONPATH`.
6. Common third-party libraries such as pandas and PyYAML may be used.

## Console commands and examples

The CLI must provide two commands:

- `check`:
  `python -m pricelab check --quotes rates\ALLFUTEu_M1_2025.csv --params rates\params.yaml`
- `adjust`:
  `python -m pricelab adjust --quotes rates\ALLFUTEu_M1_2025.csv --rolls rates\ALLFUTEu_M1_2025_roll_candidates.csv`

## Example `.vscode/settings.json`

```json
{
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "${workspaceFolder}\\src"
  }
}
```

# Rules (invariants)

- The number of rows in the output equals the number of rows in the input.
- Row order does not change.
- Bar dates and times do not change.
- Adjustment changes nothing except OHLC.
- Detection does not modify the data.
- The same confirmed roll must not be applied twice.
