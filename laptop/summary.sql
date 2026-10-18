-- per-run summary. expected comes from the seq numbers, so samples < expected means packets were lost
SELECT r.id AS run, r.note,
       COUNT(s.seq)                AS samples,
       MAX(s.seq) - MIN(s.seq) + 1 AS expected,
       ROUND(AVG(s.rssi), 1)       AS avg_rssi_dbm,
       MAX(s.throttle)             AS max_throttle
FROM runs r
JOIN samples s ON s.run_id = r.id
GROUP BY r.id;