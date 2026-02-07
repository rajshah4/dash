---
name: dash-schema
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
- sql
- query
- table
- schema
- database
- drivers
- constructors
- race
- championship
- f1
- formula
---

## Available Tables

| Table | Rows | Description |
|-------|------|-------------|
| `drivers_championship` | ~1,400 | Driver championship standings 1950-2020 |
| `constructors_championship` | ~600 | Constructor championship standings 1958-2020 |
| `race_wins` | ~1,000 | Individual race winners |
| `race_results` | ~25,000 | Full race results with positions, points, times |
| `fastest_laps` | ~1,000 | Fastest lap records per race |

## Critical Data Quality Gotchas

⚠️ **These WILL trip you up if you don't know about them:**

| Issue | Solution |
|-------|----------|
| `drivers_championship.position` is **TEXT** | Use `position = '1'` (with quotes!) |
| `constructors_championship.position` is **INTEGER** | Use `position = 1` (no quotes) |
| `race_results.position` is **TEXT** with special values | Can be `'Ret'`, `'DSQ'`, `'DNS'`, `'NC'` — filter with regex before casting |
| `race_wins.date` is **TEXT** in `'DD Mon YYYY'` format | Use `TO_DATE(date, 'DD Mon YYYY')` to extract year |
| Driver tag columns have different names | `race_wins` and `race_results` use `name_tag`; `drivers_championship` and `fastest_laps` use `driver_tag` |
| Team names vary across years | e.g., `'McLaren'` vs `'McLaren-Mercedes'` |
| Points systems changed over time | Direct cross-era point comparisons are misleading |
| Constructors Championship started in 1958 | No data before that year |

## Business Rules

- The Constructors Championship started in 1958 — no data before that year
- Points systems have changed over the years — direct cross-era comparisons are misleading
- Team names vary slightly across years (e.g., 'McLaren' vs 'McLaren-Mercedes')
- The `race_wins` table only contains wins — use `race_results` for other positions
- A 'season' or 'year' refers to a Formula 1 championship year (typically March-November)
- DNFs in `race_results` have `time = 'DNF'` — filter on `time = 'DNF'` rather than position
