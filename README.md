# PriceLab

Консольная утилита для поиска склеек в непрерывном фьючерсном ряду и
back-adjustment подтверждённых склеек. Входные данные — MT5 CSV/TSV.

PriceLab не принимает торговое решение автоматически:

1. `check` находит кандидатов по настроенным точкам поиска и размеру гэпа;
2. пользователь выбирает подтверждённые даты;
3. `adjust` корректирует историческую часть OHLC-ряда.

Точное ожидаемое поведение описано в
[спецификации](docs/spec.md).

## Установка

Требуется Python 3.11 или новее.

```powershell
python -m pip install -e .
```

## Запуск

```powershell
python -m pricelab check `
  --quotes rates\Si\SiM6_M1_2026.csv `
  --params rates\params.yaml

python -m pricelab adjust `
  --quotes rates\Si\SiM6_M1_2026.csv `
  --rolls rates\Si\SiM6_M1_2026_roll_candidates.csv
```

Пример параметров:

```yaml
baselineDeep: 300
gapMultiplier: 100
searchPoints:
  - day_change
  - fixed_time = 13:59
```

`rates/params.yaml` — рабочий конфиг. Его значения подбираются под конкретный
фьючерс и не используются тестами как неизменный эталон.

## Проверки

```powershell
python -m pytest -q
```

Для запуска тестов нужен необязательный пакет разработки:

```powershell
python -m pip install -e ".[dev]"
```

`rates/Si/SiM6_M1_2026.csv` намеренно включён в репозиторий как эталонный
набор реальных данных для проверки полного сценария `check → adjust`.

Соглашение о качестве кода описано в [docs/code_quality.md](docs/code_quality.md).
