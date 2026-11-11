"""Print a few event windows and extreme day-0 abnormal returns so the
SQL results can be checked by hand against a price chart.

Run after src/build_events.py:  python src/spot_check.py
"""

import duckdb
import pandas as pd

from config import DB_PATH

# (ticker, announce_date) of events to print in full
EXAMPLES = [("NVDA", "2023-05-24"), ("CVX", "2023-07-23")]


def pct(x: float) -> str:
    return "" if pd.isna(x) else f"{x:+.2%}"


def print_window(con, ticker: str, announce_date: str) -> None:
    df = con.execute("""
        SELECT rel_day, date, stock_ret, spy_ret, ar, timing, day0
        FROM abnormal_returns
        WHERE ticker = ? AND announce_date = CAST(? AS DATE)
        ORDER BY rel_day
    """, [ticker, announce_date]).df()
    if df.empty:
        print(f"\n{ticker} {announce_date}: no event found")
        return
    timing, day0 = df.loc[0, "timing"], df.loc[0, "day0"]
    print(f"\n=== {ticker}  announced {announce_date} ({timing})  ->  day 0 = {day0:%Y-%m-%d %a} ===")
    out = df[["rel_day", "date", "stock_ret", "spy_ret", "ar"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d %a")
    for c in ("stock_ret", "spy_ret", "ar"):
        out[c] = out[c].map(pct)
    print(out.to_string(index=False))
    car = con.execute("""
        SELECT car_m1_p1, car_m5_p5 FROM car
        WHERE ticker = ? AND announce_date = CAST(? AS DATE)
    """, [ticker, announce_date]).fetchone()
    print(f"CAR[-1,+1] = {pct(car[0])}   CAR[-5,+5] = {pct(car[1])}")


def print_extremes(con, order: str, label: str) -> None:
    df = con.execute(f"""
        SELECT ticker, announce_date, timing, date AS day0, stock_ret, spy_ret, ar
        FROM abnormal_returns
        WHERE rel_day = 0
        ORDER BY ar {order}
        LIMIT 5
    """).df()
    for c in ("stock_ret", "spy_ret", "ar"):
        df[c] = df[c].map(pct)
    print(f"\n=== 5 {label} day-0 abnormal returns ===")
    print(df.to_string(index=False))


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for ticker, d in EXAMPLES:
        print_window(con, ticker, d)
    print_extremes(con, "DESC", "largest")
    print_extremes(con, "ASC", "smallest")
    con.close()


if __name__ == "__main__":
    main()
