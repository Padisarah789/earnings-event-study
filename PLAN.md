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

## Next: event windows and abnormal returns (in SQL)

- [ ] Daily returns table from `prices`
- [ ] Map each event to its event day 0: the announce date if BMO, the next trading day if AMC (and the next trading day if the announce date is not a trading day, e.g. CVX 2023-07-23)
- [ ] Estimation window (e.g. trading days -250 to -30) and event windows (e.g. [-1,+1], [-5,+5])
- [ ] Market-model alpha/beta per event, estimated against SPY
- [ ] Abnormal returns (AR) and cumulative abnormal returns (CAR)
- [ ] Average CAR across events, with t-statistics
- [ ] Notebook with charts and write-up
