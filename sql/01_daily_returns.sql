-- daily_returns: one row per ticker per trading day.
--   day_idx: 1 for the ticker's first trading day, 2 for the next, ...
--            Lets us move N trading days forward/back with simple arithmetic.
--   ret:     simple daily return, adj_close / previous adj_close - 1.
--            NULL on each ticker's first day (no previous price).
CREATE OR REPLACE TABLE daily_returns AS
SELECT
    ticker,
    date,
    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date)                  AS day_idx,
    adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) - 1 AS ret
FROM prices
ORDER BY ticker, date;
