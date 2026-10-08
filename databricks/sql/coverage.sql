-- Run after USE CATALOG <reviewed catalog>; USE SCHEMA <reviewed Scout schema>.
-- Statistical availability, not proof of football validity/public display rights.
SELECT league, season, COUNT(*) AS stints, COUNT(DISTINCT player_id) AS players,
       SUM(minutes) AS observed_minutes,
       SUM(CASE WHEN minutes >= 450 THEN 1 ELSE 0 END) AS exposed_stints
FROM silver_player_stints
GROUP BY league, season;

SELECT role, release_id, COUNT(*) AS profiles, AVG(coverage) AS mean_coverage,
       MIN(coverage) AS minimum_coverage
FROM gold_role_profiles
GROUP BY role, release_id;
