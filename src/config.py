"""Shared settings: universe, date range, and file paths."""

from pathlib import Path

# Current Dow Jones Industrial Average members (checked 2026-11-10).
# Alphabet (GOOGL) replaced Verizon (VZ) on 2026-06-29.
DOW30 = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GOOGL", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "WMT",
]
BENCHMARK = "SPY"

START_DATE = "2023-01-01"
END_DATE = "2025-12-31"  # inclusive

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PRICES_CSV = RAW_DIR / "prices.csv"
EARNINGS_CSV = RAW_DIR / "earnings_dates.csv"
DB_PATH = ROOT / "data" / "earnings.duckdb"

# Each company reports once a quarter, so 3 years should give about 12 events.
# Allow one fewer for quarters that fall just outside the window.
MIN_EXPECTED_EVENTS = 11
