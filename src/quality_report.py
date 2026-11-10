"""Print data quality checks for the DuckDB tables.

Run: python src/quality_report.py
"""

import duckdb

from config import DB_PATH, MIN_EXPECTED_EVENTS

LARGE_MOVE = 0.15  # flag daily returns above 15% in either direction


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def show(con, sql: str) -> None:
    df = con.sql(sql).df()
    print("(none)" if df.empty else df.to_string(index=False))


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)

    section("Row counts per table")
    show(con, """
        SELECT 'prices' AS table_name, COUNT(*) AS rows FROM prices
        UNION ALL
        SELECT 'events', COUNT(*) FROM events
    """)

    section("Prices: rows and date range per ticker")
    show(con, """
        SELECT ticker, COUNT(*) AS rows, MIN(date) AS first_date,
               MAX(date) AS last_date
        FROM prices GROUP BY ticker ORDER BY ticker
    """)

    section("Prices: tickers with a different number of trading days than SPY")
    show(con, """
        WITH c AS (SELECT ticker, COUNT(*) AS n FROM prices GROUP BY ticker)
        SELECT c.ticker, c.n AS rows, s.n AS spy_rows
        FROM c, (SELECT n FROM c WHERE ticker = 'SPY') s
        WHERE c.n <> s.n
    """)

    section("Events per ticker (with timing breakdown)")
    show(con, """
        SELECT ticker, COUNT(*) AS events,
               COUNT(*) FILTER (WHERE timing = 'BMO')     AS bmo,
               COUNT(*) FILTER (WHERE timing = 'AMC')     AS amc,
               COUNT(*) FILTER (WHERE timing = 'DMH')     AS dmh,
               COUNT(*) FILTER (WHERE timing = 'unknown') AS unknown,
               MIN(announce_date) AS first_event,
               MAX(announce_date) AS last_event
        FROM events GROUP BY ticker ORDER BY ticker
    """)

    section("Missing values")
    show(con, """
        SELECT 'prices' AS table_name, 'ticker' AS col, COUNT(*) FILTER (WHERE ticker IS NULL) AS nulls FROM prices
        UNION ALL SELECT 'prices', 'date', COUNT(*) FILTER (WHERE date IS NULL) FROM prices
        UNION ALL SELECT 'prices', 'adj_close', COUNT(*) FILTER (WHERE adj_close IS NULL) FROM prices
        UNION ALL SELECT 'events', 'ticker', COUNT(*) FILTER (WHERE ticker IS NULL) FROM events
        UNION ALL SELECT 'events', 'announce_date', COUNT(*) FILTER (WHERE announce_date IS NULL) FROM events
        UNION ALL SELECT 'events', 'timing', COUNT(*) FILTER (WHERE timing IS NULL OR timing = 'unknown') FROM events
    """)

    section("Duplicates")
    show(con, """
        SELECT 'prices (ticker, date)' AS key, COUNT(*) AS duplicate_keys FROM (
            SELECT ticker, date FROM prices GROUP BY ALL HAVING COUNT(*) > 1)
        UNION ALL
        SELECT 'events (ticker, announce_date)', COUNT(*) FROM (
            SELECT ticker, announce_date FROM events GROUP BY ALL HAVING COUNT(*) > 1)
    """)

    section("Events that are not trading days (weekend/holiday)")
    show(con, """
        SELECT e.ticker, e.announce_date, e.timing
        FROM events e
        WHERE e.announce_date NOT IN (SELECT date FROM prices WHERE ticker = 'SPY')
        ORDER BY e.ticker, e.announce_date
    """)

    section("Events closer than 60 days apart (possible duplicates or bad dates)")
    show(con, """
        SELECT ticker, prev_date, announce_date, announce_date - prev_date AS days_apart
        FROM (SELECT ticker, announce_date,
                     LAG(announce_date) OVER (PARTITION BY ticker ORDER BY announce_date) AS prev_date
              FROM events)
        WHERE announce_date - prev_date < 60
    """)

    section("Manual corrections (data/corrections.csv)")
    show(con, """
        SELECT ticker, announce_date, field, old_value, new_value,
               CASE WHEN old_value = new_value THEN 'verified' ELSE 'corrected' END AS action
        FROM corrections ORDER BY ticker, announce_date
    """)

    section("Events whose timing differs from the ticker's usual timing")
    show(con, """
        WITH usual AS (
            SELECT ticker, MODE(timing) AS usual_timing FROM events GROUP BY ticker)
        SELECT e.ticker, e.announce_date, e.timing, u.usual_timing,
               c.ticker IS NOT NULL AS manually_checked
        FROM events e JOIN usual u USING (ticker)
        LEFT JOIN corrections c
               ON c.ticker = e.ticker AND CAST(c.announce_date AS DATE) = e.announce_date
        WHERE e.timing <> u.usual_timing
        ORDER BY e.ticker, e.announce_date
    """)

    section("Events during market hours (DMH) or with unknown timing")
    show(con, """
        SELECT ticker, announce_date, timing FROM events
        WHERE timing NOT IN ('BMO', 'AMC') OR timing IS NULL
        ORDER BY ticker, announce_date
    """)

    section(f"Daily price moves larger than {LARGE_MOVE:.0%} (check splits/spin-offs)")
    show(con, f"""
        SELECT ticker, date, ROUND(ret, 4) AS daily_return
        FROM (SELECT ticker, date,
                     adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) - 1 AS ret
              FROM prices)
        WHERE ABS(ret) > {LARGE_MOVE}
        ORDER BY ticker, date
    """)

    section(f"Tickers with fewer than {MIN_EXPECTED_EVENTS} events")
    show(con, f"""
        WITH t AS (SELECT DISTINCT ticker FROM prices WHERE ticker <> 'SPY')
        SELECT t.ticker, COUNT(e.ticker) AS events
        FROM t LEFT JOIN events e USING (ticker)
        GROUP BY t.ticker HAVING COUNT(e.ticker) < {MIN_EXPECTED_EVENTS}
        ORDER BY t.ticker
    """)

    con.close()


if __name__ == "__main__":
    main()
