# Plan

Earnings event study on the 30 current Dow Jones Industrial Average stocks,
with SPY as the market benchmark, 2023-01-01 to 2025-12-31.

## Done: data setup (2026-11-10)

- [x] Python project: `.venv`, `requirements.txt`, `.gitignore`, `src/`, `data/raw/`, `notebooks/`
- [x] `src/download.py`: adjusted close prices and earnings dates from Yahoo Finance (yfinance)
- [x] `src/load.py`: load CSVs into DuckDB tables `prices` and `events`
- [x] `src/quality_report.py`: row counts, date ranges, events per ticker, missing values, duplicates, sanity checks

## Open data issues (decide before analysis)

Yahoo data that looks wrong. It has **not** been corrected in the data yet:

- [ ] CVX 2023-07-23 is a Sunday. Chevron's Q2 2023 release appears to be 2023-07-28, before the open. Verify and fix.
- [ ] AMGN 2023-10-31 is labelled before open. Amgen normally reports after close. Verify.
- [ ] AMZN 2024-08-01 is labelled midday (12:00). Amazon normally reports after close. Verify.
- [ ] AXP 2024-04-19 is labelled midday (10:00). AXP normally reports before the open. Verify.
- [ ] Decide on a second source to cross-check all 360 dates (e.g. SEC 8-K Item 2.02 filing dates), or document Yahoo as the only source.
- [ ] Note the survivorship bias: the universe is the *current* Dow (GOOGL joined 2026-06-29, NVDA and SHW joined 2024-11-08, AMZN joined 2024-02-26), not the members at each event date.

## Next: event windows and abnormal returns (in SQL)

- [ ] Daily returns table from `prices`
- [ ] Map each event to its event day 0: the announce date if BMO, the next trading day if AMC
- [ ] Estimation window (e.g. trading days -250 to -30) and event windows (e.g. [-1,+1], [-5,+5])
- [ ] Market-model alpha/beta per event, estimated against SPY
- [ ] Abnormal returns (AR) and cumulative abnormal returns (CAR)
- [ ] Average CAR across events, with t-statistics
- [ ] Notebook with charts and write-up
