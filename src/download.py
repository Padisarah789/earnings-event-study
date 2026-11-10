"""Download daily adjusted close prices and earnings announcement dates.

Source: Yahoo Finance via the yfinance package (unofficial, scraped API).
Outputs (in data/raw/):
  prices.csv          ticker, date, adj_close
  earnings_dates.csv  ticker, announce_datetime, announce_date, timing,
                      eps_estimate, reported_eps, surprise_pct
  download_log.csv    one row per ticker and dataset with status and row count

Run: python src/download.py
"""

import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from config import (BENCHMARK, DOW30, EARNINGS_CSV, END_DATE, PRICES_CSV,
                    RAW_DIR, START_DATE)

# From now back to early 2023 is about 16 quarters, plus one or two future
# dates. Ask for plenty so the start of the window is covered.
EARNINGS_LIMIT = 40


def classify_timing(ts: pd.Timestamp) -> str:
    """Label an announcement time (US/Eastern) relative to the trading session.

    BMO = before market open (before 09:30), AMC = after market close
    (16:00 or later), DMH = during market hours. Yahoo uses midnight when
    it has no time, so midnight is 'unknown'.
    """
    t = ts.time()
    if t.hour == 0 and t.minute == 0:
        return "unknown"
    if (t.hour, t.minute) < (9, 30):
        return "BMO"
    if t.hour >= 16:
        return "AMC"
    return "DMH"


def download_prices(tickers: list[str], log: list[dict]) -> pd.DataFrame:
    # yfinance's end date is exclusive, so add one day.
    end_exclusive = (pd.Timestamp(END_DATE) + timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(
        tickers,
        start=START_DATE,
        end=end_exclusive,
        auto_adjust=False,  # keep the separate 'Adj Close' column
        progress=False,
        group_by="column",
        threads=True,
    )
    adj = raw["Adj Close"]
    frames = []
    for t in tickers:
        s = adj[t].dropna() if t in adj.columns else pd.Series(dtype=float)
        log.append({"ticker": t, "dataset": "prices",
                    "status": "ok" if len(s) else "EMPTY", "rows": len(s)})
        if len(s):
            frames.append(pd.DataFrame({"ticker": t, "date": s.index.date,
                                        "adj_close": s.values}))
    return pd.concat(frames, ignore_index=True)


def download_earnings(ticker: str, log: list[dict]) -> pd.DataFrame | None:
    for attempt in range(3):
        try:
            df = yf.Ticker(ticker).get_earnings_dates(limit=EARNINGS_LIMIT)
            break
        except Exception as e:  # network or parsing errors from Yahoo
            err = repr(e)
            time.sleep(2 * (attempt + 1))
    else:
        log.append({"ticker": ticker, "dataset": "earnings",
                    "status": f"ERROR {err}", "rows": 0})
        return None

    if df is None or df.empty:
        log.append({"ticker": ticker, "dataset": "earnings",
                    "status": "EMPTY", "rows": 0})
        return None

    df = df.reset_index().rename(columns={
        "Earnings Date": "announce_datetime",
        "EPS Estimate": "eps_estimate",
        "Reported EPS": "reported_eps",
        "Surprise(%)": "surprise_pct",
    })
    ts = pd.to_datetime(df["announce_datetime"])
    if ts.dt.tz is not None:
        ts = ts.dt.tz_convert("America/New_York")
    df["announce_datetime"] = ts
    df["announce_date"] = ts.dt.date
    df["timing"] = ts.map(classify_timing)
    df.insert(0, "ticker", ticker)

    in_window = (df["announce_date"] >= pd.Timestamp(START_DATE).date()) & \
                (df["announce_date"] <= pd.Timestamp(END_DATE).date())
    df = df[in_window]

    # Warn if Yahoo's history doesn't reach back to the window start.
    oldest = ts.min().date()
    status = "ok"
    if oldest > pd.Timestamp(START_DATE).date() + timedelta(days=90):
        status = f"WARN history starts {oldest}"
    log.append({"ticker": ticker, "dataset": "earnings",
                "status": status, "rows": len(df)})
    return df[["ticker", "announce_datetime", "announce_date", "timing",
               "eps_estimate", "reported_eps", "surprise_pct"]]


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log: list[dict] = []

    print(f"Downloading prices for {len(DOW30)} stocks + {BENCHMARK} ...")
    prices = download_prices(DOW30 + [BENCHMARK], log)
    prices.to_csv(PRICES_CSV, index=False)
    print(f"  saved {len(prices):,} rows -> {PRICES_CSV.relative_to(RAW_DIR.parent.parent)}")

    print(f"Downloading earnings dates for {len(DOW30)} stocks ...")
    frames = []
    for t in DOW30:  # SPY is an ETF and has no earnings
        df = download_earnings(t, log)
        if df is not None:
            frames.append(df)
        time.sleep(0.5)  # be gentle with Yahoo
    earnings = pd.concat(frames, ignore_index=True)
    earnings.to_csv(EARNINGS_CSV, index=False)
    print(f"  saved {len(earnings):,} rows -> {EARNINGS_CSV.relative_to(RAW_DIR.parent.parent)}")

    log_df = pd.DataFrame(log)
    log_df["downloaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_df["yfinance_version"] = yf.__version__
    log_df.to_csv(RAW_DIR / "download_log.csv", index=False)

    problems = log_df[log_df["status"] != "ok"]
    if len(problems):
        print("\nProblems during download:")
        print(problems[["ticker", "dataset", "status", "rows"]].to_string(index=False))
        return 1
    print("\nAll downloads OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
