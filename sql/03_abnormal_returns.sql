-- abnormal_returns: one row per event per relative trading day, -5 to +5.
--   ar = stock return - SPY return (market-adjusted abnormal return).
-- LEFT JOINs keep all 11 rows per event even if a price is missing, so gaps
-- show up as NULLs (caught by the quality report) instead of vanishing.
CREATE OR REPLACE TABLE abnormal_returns AS
SELECT
    ed.event_id,
    ed.ticker,
    ed.announce_date,
    ed.timing,
    ed.day0,
    w.rel_day,
    s.date,
    s.ret          AS stock_ret,
    m.ret          AS spy_ret,
    s.ret - m.ret  AS ar
FROM event_days ed
CROSS JOIN (SELECT range AS rel_day FROM range(-5, 6)) w   -- -5, -4, ..., +5
LEFT JOIN daily_returns s
  ON s.ticker  = ed.ticker
 AND s.day_idx = ed.day0_idx + w.rel_day
LEFT JOIN daily_returns m
  ON m.ticker = 'SPY'
 AND m.date   = s.date
ORDER BY ed.event_id, w.rel_day;
