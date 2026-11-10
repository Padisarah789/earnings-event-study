"""Load the raw CSVs into a DuckDB database file (data/earnings.duckdb).

Tables:
  prices(ticker, date, adj_close)
  events(ticker, announce_date, timing)

The tables are rebuilt from scratch on every run. Duplicates are NOT removed
here, so the quality report can find them.

Run: python src/load.py
"""

import duckdb

from config import DB_PATH, EARNINGS_CSV, PRICES_CSV


def main() -> None:
    con = duckdb.connect(str(DB_PATH))

    con.execute("""
        CREATE OR REPLACE TABLE prices (
            ticker    VARCHAR NOT NULL,
            date      DATE    NOT NULL,
            adj_close DOUBLE
        )
    """)
    con.execute("""
        INSERT INTO prices
        SELECT ticker, CAST(date AS DATE), CAST(adj_close AS DOUBLE)
        FROM read_csv(?, header = true)
    """, [str(PRICES_CSV)])

    con.execute("""
        CREATE OR REPLACE TABLE events (
            ticker        VARCHAR NOT NULL,
            announce_date DATE    NOT NULL,
            timing        VARCHAR   -- BMO, AMC, DMH or unknown
        )
    """)
    con.execute("""
        INSERT INTO events
        SELECT ticker, CAST(announce_date AS DATE), timing
        FROM read_csv(?, header = true)
    """, [str(EARNINGS_CSV)])

    for table in ("prices", "events"):
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n:,} rows loaded")
    con.close()
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
