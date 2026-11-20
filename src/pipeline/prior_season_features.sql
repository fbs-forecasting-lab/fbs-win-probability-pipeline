-- One injected partition contains exactly one verified source per season.
-- Outcomes enter the label CTE only; target scores never enter feature expressions.
WITH selected AS (
  SELECT * FROM __TABLE__ WHERE selection_id = '__SELECTION__'
), perspectives AS (
  SELECT season, home_id AS team_id,
         CASE WHEN home_points > away_points THEN 1 ELSE 0 END AS win,
         home_points - away_points AS margin, start_epoch_us AS started
  FROM selected WHERE completed = true AND season BETWEEN 2021 AND 2025
  UNION ALL
  SELECT season, away_id AS team_id,
         CASE WHEN away_points > home_points THEN 1 ELSE 0 END AS win,
         away_points - home_points AS margin, start_epoch_us AS started
  FROM selected WHERE completed = true AND season BETWEEN 2021 AND 2025
), aggregates AS (
  SELECT season, team_id, count(*) AS games,
         CAST(sum(win) AS DOUBLE) / count(*) AS win_pct,
         CAST(sum(margin) AS DOUBLE) / count(*) AS avg_margin,
         max(started) AS latest
  FROM perspectives GROUP BY season, team_id
), features AS (
  SELECT t.id AS game_id, t.season, t.start_date AS cutoff, t.start_epoch_us AS cutoff_epoch_us,
         CASE WHEN t.season <= 2024 THEN 'train' WHEN t.season = 2025 THEN 'holdout' ELSE 'prediction' END AS split,
         h.win_pct - a.win_pct AS prior_win_pct_diff,
         h.avg_margin - a.avg_margin AS prior_avg_margin_diff,
         CASE WHEN t.neutral_site THEN 0 ELSE 1 END AS home_field,
         coalesce(h.games, 0) AS home_prior_game_count, coalesce(a.games, 0) AS away_prior_game_count,
         CASE WHEN t.season < 2026 AND NOT t.completed THEN 1 ELSE 0 END AS target_uncompleted,
         CASE WHEN t.season = 2026 AND t.completed THEN 1 ELSE 0 END AS prediction_target_completed,
         CASE WHEN h.games IS NULL THEN 1 ELSE 0 END AS missing_home_history,
         CASE WHEN a.games IS NULL THEN 1 ELSE 0 END AS missing_away_history,
         CASE WHEN h.latest >= t.start_epoch_us THEN 1 ELSE 0 END AS home_history_not_before_cutoff,
         CASE WHEN a.latest >= t.start_epoch_us THEN 1 ELSE 0 END AS away_history_not_before_cutoff
  FROM selected t
  LEFT JOIN aggregates h ON h.season = t.season - 1 AND h.team_id = t.home_id
  LEFT JOIN aggregates a ON a.season = t.season - 1 AND a.team_id = t.away_id
  WHERE t.season BETWEEN 2022 AND 2026
), labels AS (
  SELECT id, season, CASE WHEN season < 2026 AND completed
    THEN CASE WHEN home_points > away_points THEN 1 ELSE 0 END ELSE NULL END AS home_win
  FROM selected WHERE season BETWEEN 2022 AND 2026
)
SELECT f.*, l.home_win FROM features f JOIN labels l ON l.id = f.game_id AND l.season = f.season
ORDER BY f.season, f.cutoff_epoch_us, f.game_id
