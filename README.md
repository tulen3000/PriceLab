# PriceLab v2

Реализация по `docs/mini_spec_v2.md`.

## Зависимости

- pandas
- PyYAML

## Запуск

Если `src` уже добавлен в `PYTHONPATH`:

```powershell
python -m pricelab check --quotes rates\ALLFUTEu_M1_2025.csv --params rates\params.yaml
python -m pricelab adjust --quotes rates\ALLFUTEu_M1_2025.csv --rolls rates\ALLFUTEu_M1_2025_roll_candidates.csv
```

## Пример params.yaml

```yaml
baselineDeep: 50
gapMultiplier: 5
searchPoints:
  - day_change
  - fixed_time = 13:59
```


Spec used in this build: `docs/mini_spec_v2_1.md`
