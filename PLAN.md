# Plan

Earnings event study on the 30 current Dow Jones Industrial Average stocks,
with SPY as the market benchmark, 2023-01-01 to 2025-12-31.

## Done: data setup (2026-11-10)

- [x] Python project: `.venv`, `requirements.txt`, `.gitignore`, `src/`, `data/raw/`, `notebooks/`
- [x] `src/download.py`: adjusted close prices and earnings dates from Yahoo Finance (yfinance)
- [x] `src/load.py`: load CSVs into DuckDB tables `prices` and `events`
- [x] `src/quality_report.py`: row counts, date ranges, events per ticker, missing values, duplicates, sanity checks

## Done: manual corrections (2026-11-10)

The raw CSVs are never edited. Manual fixes are recorded in `data/corrections.csv`
(committed) and applied by `src/load.py`. The load stops if a correction no
longer matches the raw data.

- [x] CVX 2023-07-23 (Sunday, AMC): verified, no change. Chevron released preliminary Q2 results that Sunday evening. The event day must roll forward to the next trading day (2023-07-24).
- [x] AMGN 2023-10-31 (BMO): verified, no change. Amgen released before the open that quarter.
- [x] AMZN 2024-08-01: timing corrected from DMH to AMC (Amazon IR, Q2 2024 results).
- [x] AXP 2024-04-19: timing corrected from DMH to BMO (American Express Business Wire, Q1 2024 results).
- [x] Quality report confirms there are no DMH or unknown-timing events left.

## Open data issues

- [ ] Decide on a second source to cross-check all 360 dates (e.g. SEC 8-K Item 2.02 filing dates), or document Yahoo as the only source. Only the 4 flagged records were checked by hand.
- [x] DIS switched from AMC to BMO in 2024: verified at the switch point (2024-02-07 AMC, 2024-05-07 BMO), no change.
- [ ] Note the survivorship bias: the universe is the *current* Dow (GOOGL joined 2026-06-29, NVDA and SHW joined 2024-11-08, AMZN joined 2024-02-26), not the members at each event date.

## Done: event windows and abnormal returns in SQL (2026-11-11)

Run order: `load.py` -> `build_events.py` -> `quality_report.py` / `spot_check.py`.

- [x] `sql/01_daily_returns.sql`: daily returns plus a per-ticker trading-day index
- [x] `sql/02_event_days.sql`: day 0 is the announce date for BMO and the next trading day for AMC. Non-trading dates roll forward to the next trading day.
- [x] `sql/03_abnormal_returns.sql`: 11 rows per event (-5..+5 trading days), AR = stock return - SPY return (market-adjusted model)
- [x] `sql/04_car.sql`: CAR[-1,+1] and CAR[-5,+5] per event, as a simple sum of daily ARs
- [x] Quality checks: 11 rows per event, no missing returns, day 0 is always a trading day. All pass for the 360 events.
- [x] `src/spot_check.py`: NVDA 2023-05-24 and CVX 2023-07-23 windows, plus the top/bottom 5 day-0 ARs, for hand checking

Notes:
- CVX 2023-07-23 was a preliminary Sunday release. Chevron's full Q2 results (Fri 2023-07-28) fall at day +4 of the same window, so CAR[-5,+5] mixes the two announcements.
- AR uses the market-adjusted model (beta = 1 for every stock). A market model with estimated alpha/beta is an optional upgrade.

## Next: statistics and presentation

- [ ] Average AR by relative day and average CAR across events
- [ ] t-statistics (cross-sectional), possibly split by BMO/AMC or by sector
- [ ] Optional: market-model alpha/beta per event (estimation window e.g. -250 to -30)
- [ ] Notebook with charts and write-up

## Log

- 2026-11-11 — Day 2: event windows and abnormal returns built in SQL; NVDA and CVX windows verified by hand.
