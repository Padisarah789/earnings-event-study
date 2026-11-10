"""Load the raw CSVs into a DuckDB database file (data/earnings.duckdb).

Tables:
  prices(ticker, date, adj_close)
  events(ticker, announce_date, timing)
  corrections  copy of data/corrections.csv, for reference

The tables are rebuilt from scratch on every run. The raw CSVs are never
edited: manual fixes live in data/corrections.csv and are applied here.
Duplicates are NOT removed, so the quality report can find them.

Run: python src/load.py
"""

import sys

import duckdb

from config import CORRECTIONS_CSV, DB_PATH, EARNINGS_CSV, PRICES_CSV

# Columns of `events` that a correction may change.
CORRECTABLE_FIELDS = {"timing"}


def apply_corrections(con: duckdb.DuckDBPyConnection) -> None:
    """Apply data/corrections.csv to the events table.

    Every row must match exactly one event whose current value equals
    old_value. Rows with old_value == new_value are checks only ("verified,
    no change"). Any mismatch stops the load, because it means the raw data
    changed since the correction was written.
    """
    con.execute("""
        CREATE OR REPLACE TABLE corrections AS
        SELECT * FROM read_csv(?, header = true, all_varchar = true)
    """, [str(CORRECTIONS_CSV)])
    rows = con.execute("""
        SELECT ticker, announce_date, field, old_value, new_value
        FROM corrections ORDER BY ticker, announce_date
    """).fetchall()

    errors = []
    for ticker, date, field, old, new in rows:
        label = f"{ticker} {date} {field}"
        if field not in CORRECTABLE_FIELDS:
            errors.append(f"{label}: field not allowed (allowed: {sorted(CORRECTABLE_FIELDS)})")
            continue
        found = con.execute(f"""
            SELECT {field} FROM events
            WHERE ticker = ? AND announce_date = CAST(? AS DATE)
        """, [ticker, date]).fetchall()
        if len(found) != 1:
            errors.append(f"{label}: expected 1 matching event, found {len(found)}")
            continue
        current = found[0][0]
        if current != old:
            errors.append(f"{label}: expected old value {old!r}, found {current!r}")
            continue
        if old == new:
            print(f"  verified  {label} = {old}")
        else:
            con.execute(f"""
                UPDATE events SET {field} = ?
                WHERE ticker = ? AND announce_date = CAST(? AS DATE)
            """, [new, ticker, date])
            print(f"  corrected {label}: {old} -> {new}")

    if errors:
        print("\nCorrections could not be applied:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)


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

    print("Applying corrections:")
    apply_corrections(con)

    for table in ("prices", "events"):
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n:,} rows loaded")
    con.close()
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
