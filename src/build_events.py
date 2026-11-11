"""Build the event-study tables by running the SQL files in sql/ in order.

Creates (in data/earnings.duckdb):
  daily_returns     ticker, date, day_idx, ret
  event_days        event_id, ticker, announce_date, timing, day0, day0_idx
  abnormal_returns  one row per event per relative day -5..+5
  car               one row per event, CAR[-1,+1] and CAR[-5,+5]

Run after src/load.py:  python src/build_events.py
"""

import duckdb

from config import DB_PATH, SQL_DIR


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    for path in sorted(SQL_DIR.glob("*.sql")):
        con.execute(path.read_text())
        # Each file creates one table named after the file, minus the number.
        table = path.stem.split("_", 1)[1]
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{path.name:<24} -> {table}: {n:,} rows")
    con.close()


if __name__ == "__main__":
    main()
