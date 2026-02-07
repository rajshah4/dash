

-- <query name>driver_champion_summary_by_year</query name>
-- <query description>
-- Returns the drivers’ champion for a given year with team, points, wins that season, and total career titles. Handles drivers_championship.position as TEXT and parses race_wins.date. Update the year filter in the CTE to reuse.
-- Tables: drivers_championship, race_wins
-- </query description>
-- <query>
WITH champion AS (
  SELECT year, name, team, points
  FROM drivers_championship
  WHERE year = 2020 AND position = '1'
),
wins AS (
  SELECT COUNT(*) AS wins
  FROM race_wins rw
  JOIN champion c ON c.name = rw.name
  WHERE EXTRACT(YEAR FROM TO_DATE(rw.date, 'DD Mon YYYY')) = 2020
),
titles AS (
  SELECT COUNT(*) AS titles
  FROM drivers_championship dc
  WHERE dc.position = '1'
    AND dc.name = (SELECT name FROM champion)
)
SELECT
  c.name AS champion_name,
  c.team,
  c.points,
  COALESCE(w.wins, 0) AS race_wins_2020,
  t.titles AS career_titles
FROM champion c
LEFT JOIN wins w ON TRUE
LEFT JOIN titles t ON TRUE
LIMIT 1
-- </query>
