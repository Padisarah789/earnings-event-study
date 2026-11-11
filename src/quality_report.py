"""Print data quality checks for the DuckDB tables.

Run: python src/quality_report.py
"""

import duckdb

from config import DB_PATH, MIN_EXPECTED_EVENTS, WINDOW_END, WINDOW_START

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

    event_checks(con)
    con.close()


def event_checks(con) -> None:
    """Checks on the tables built by src/build_events.py."""
    built = {r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables").fetchall()}
    needed = {"daily_returns", "event_days", "abnormal_returns", "car"}
    if not needed <= built:
        print(f"\n(Event tables not built yet: run src/build_events.py. "
              f"Missing: {', '.join(sorted(needed - built))})")
        return

    n_days = WINDOW_END - WINDOW_START + 1

    section(f"Events without exactly {n_days} window rows")
    show(con, f"""
        SELECT ed.ticker, ed.announce_date, COUNT(ar.rel_day) AS rows
        FROM event_days ed
        LEFT JOIN abnormal_returns ar USING (event_id)
        GROUP BY ALL
        HAVING COUNT(ar.rel_day) <> {n_days}
        ORDER BY ed.ticker, ed.announce_date
    """)

    section("Events missing from event_days (lost between events and the windows)")
    show(con, """
        SELECT e.ticker, e.announce_date, e.timing
        FROM events e
        ANTI JOIN event_days ed USING (ticker, announce_date)
    """)

    section("Window rows with missing returns")
    show(con, """
        SELECT ticker, announce_date, rel_day, date, stock_ret, spy_ret, ar
        FROM abnormal_returns
        WHERE date IS NULL OR stock_ret IS NULL OR spy_ret IS NULL OR ar IS NULL
        ORDER BY ticker, announce_date, rel_day
    """)

    section("Day 0 that is missing, not a trading day, or before the announcement")
    show(con, """
        SELECT ticker, announce_date, timing, day0
        FROM event_days
        WHERE day0 IS NULL
           OR day0 NOT IN (SELECT date FROM daily_returns WHERE ticker = 'SPY')
           OR day0 < announce_date
           OR (timing = 'AMC' AND day0 = announce_date)
        ORDER BY ticker, announce_date
    """)

    section("Day 0 more than 4 calendar days after the announcement")
    show(con, """
        SELECT ticker, announce_date, timing, day0, day0 - announce_date AS days_later
        FROM event_days
        WHERE day0 - announce_date > 4
    """)

    section("Events with a missing CAR")
    show(con, """
        SELECT ticker, announce_date, car_m1_p1, car_m5_p5
        FROM car
        WHERE car_m1_p1 IS NULL OR car_m5_p5 IS NULL
    """)


if __name__ == "__main__":
    main()
