-- car: one row per event, cumulative abnormal return (sum of daily ARs)
-- over [-1, +1] and [-5, +5]. If any AR in a window is missing the CAR is
-- NULL rather than a sum over fewer days.
CREATE OR REPLACE TABLE car AS
SELECT
    event_id,
    ticker,
    announce_date,
    timing,
    day0,
    CASE WHEN COUNT(ar) FILTER (WHERE rel_day BETWEEN -1 AND 1) = 3
         THEN SUM(ar)   FILTER (WHERE rel_day BETWEEN -1 AND 1)
    END AS car_m1_p1,
    CASE WHEN COUNT(ar) = 11
         THEN SUM(ar)
    END AS car_m5_p5
FROM abnormal_returns
GROUP BY event_id, ticker, announce_date, timing, day0
ORDER BY event_id;
