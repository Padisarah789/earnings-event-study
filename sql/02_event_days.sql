-- event_days: one row per earnings event, with day 0 = the first trading day
-- on which the market could react.
--   BMO (before open): the announce date itself, or the next trading day
--                      if the announce date is not a trading day.
--   AMC (after close): the first trading day strictly after the announce date.
--   Any other timing:  no match, so day0 stays NULL and the quality report
--                      flags it.
CREATE OR REPLACE TABLE event_days AS
WITH first_day AS (
    SELECT
        e.ticker,
        e.announce_date,
        e.timing,
        MIN(r.date) AS day0
    FROM events e
    LEFT JOIN daily_returns r
      ON r.ticker = e.ticker
     AND CASE e.timing
             WHEN 'BMO' THEN r.date >= e.announce_date
             WHEN 'AMC' THEN r.date >  e.announce_date
         END
    GROUP BY e.ticker, e.announce_date, e.timing
)
SELECT
    ROW_NUMBER() OVER (ORDER BY f.ticker, f.announce_date) AS event_id,
    f.ticker,
    f.announce_date,
    f.timing,
    f.day0,
    r.day_idx AS day0_idx
FROM first_day f
LEFT JOIN daily_returns r
  ON r.ticker = f.ticker
 AND r.date   = f.day0
ORDER BY event_id;
