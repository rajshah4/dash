---
name: dash-sql-patterns
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
- championship
- wins
- driver
- constructor
- position
- query
---

## Validated Query Patterns

These queries are known to work against the F1 database. Use them as templates.

### Driver championships all time
```sql
SELECT name AS driver, COUNT(*) AS championship_wins
FROM drivers_championship
WHERE position = '1'  -- TEXT comparison!
GROUP BY name
ORDER BY championship_wins DESC
LIMIT 10
```

### Constructor championships all time
```sql
SELECT team, COUNT(*) AS championship_wins
FROM constructors_championship
WHERE position = 1  -- INTEGER comparison!
GROUP BY team
ORDER BY championship_wins DESC
LIMIT 10
```

### Championship race wins
```sql
SELECT dc.year, dc.name AS champion_name, COUNT(rw.name) AS race_wins
FROM drivers_championship dc
JOIN race_wins rw ON dc.name = rw.name
  AND dc.year = EXTRACT(YEAR FROM TO_DATE(rw.date, 'DD Mon YYYY'))
WHERE dc.position = '1'  -- TEXT comparison!
GROUP BY dc.year, dc.name
ORDER BY dc.year DESC
LIMIT 50
```

### Safe position filtering (TEXT column)
```sql
SELECT year, venue, name, position, points
FROM race_results
WHERE position ~ '^[0-9]+$'  -- Only numeric positions
  AND CAST(position AS INTEGER) <= 10
  AND year = 2020
ORDER BY venue, CAST(position AS INTEGER)
LIMIT 50
```
