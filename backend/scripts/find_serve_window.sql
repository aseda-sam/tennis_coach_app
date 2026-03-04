-- Find which video and serve number a serve window belongs to.
-- Usage: replace :sw_id with the serve window ID
--   psql: \set sw_id 58  then \i scripts/find_serve_window.sql
--   or:   docker compose exec postgres psql -U tennis -d tennis_coach -v sw_id=58 -f /scripts/find_serve_window.sql
--   or just copy-paste and replace :sw_id manually

WITH video_serves AS (
    SELECT
        sw.id AS serve_window_id,
        ROW_NUMBER() OVER (ORDER BY sw.start_timestamp) AS serve_number,
        COUNT(*) OVER () AS total_serves,
        sw.start_timestamp,
        sw.court_side,
        v.id AS video_id,
        v.filename,
        v.recorded_at,
        v.camera_angle
    FROM serve_windows sw
    JOIN videos v ON v.id = sw.video_id
    WHERE sw.video_id = (SELECT video_id FROM serve_windows WHERE id = :sw_id)
)
SELECT
    serve_window_id,
    serve_number || ' of ' || total_serves AS position,
    filename,
    video_id,
    camera_angle,
    recorded_at,
    CASE WHEN serve_window_id = :sw_id THEN '>>> THIS ONE <<<' ELSE '' END AS marker
FROM video_serves
ORDER BY serve_number;
