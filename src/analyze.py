"""One-sample t-tests on event-level abnormal returns.

Tests (H0: mean = 0, two-sided):
  ar_day0         abnormal return on day 0
  car_m1_p1       CAR over [-1, +1]
  car_m5_p5       CAR over [-5, +5]
  abs_ar_diff     |AR| on day 0 minus the mean |AR| over days -5..-2
                  of the same event

Prints the results table, saves it to results/summary.csv, and prints the
inputs needed to recompute each t-statistic by hand: t = mean / (sd / sqrt(n)).

Run after src/build_events.py:  python src/analyze.py
"""

import math

import duckdb
import pandas as pd
from scipy import stats

from config import DB_PATH, RESULTS_DIR

TESTS = {
    "ar_day0": "Day-0 abnormal return",
    "car_m1_p1": "CAR[-1,+1]",
    "car_m5_p5": "CAR[-5,+5]",
    "abs_ar_diff": "|AR| day 0 minus mean |AR| days -5..-2",
}

# One row per event with the four measures.
EVENT_MEASURES_SQL = """
    WITH per_event AS (
        SELECT
            event_id,
            MAX(ar)          FILTER (WHERE rel_day = 0)                AS ar_day0,
            AVG(ABS(ar))     FILTER (WHERE rel_day BETWEEN -5 AND -2)  AS mean_abs_ar_pre
        FROM abnormal_returns
        GROUP BY event_id
    )
    SELECT
        c.event_id,
        c.ticker,
        c.announce_date,
        p.ar_day0,
        c.car_m1_p1,
        c.car_m5_p5,
        ABS(p.ar_day0) - p.mean_abs_ar_pre AS abs_ar_diff
    FROM car c
    JOIN per_event p USING (event_id)
    ORDER BY c.event_id
"""


def summary_sql(col: str) -> str:
    """Descriptive statistics for one measure, computed in DuckDB."""
    return f"""
        SELECT
            COUNT({col})                         AS n,
            AVG({col})                           AS mean,
            MEDIAN({col})                        AS median,
            STDDEV_SAMP({col})                   AS std,
            AVG(CASE WHEN {col} > 0 THEN 1.0 ELSE 0.0 END)
                FILTER (WHERE {col} IS NOT NULL) AS share_positive
        FROM event_measures
    """


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute(f"CREATE TEMP TABLE event_measures AS {EVENT_MEASURES_SQL}")
    events = con.execute("SELECT * FROM event_measures").df()

    rows = []
    for col, label in TESTS.items():
        n, mean, median, std, share_pos = con.execute(summary_sql(col)).fetchone()
        values = events[col].dropna()
        t_stat, p_value = stats.ttest_1samp(values, popmean=0.0)

        # Cross-check scipy against the textbook formula.
        t_manual = mean / (std / math.sqrt(n))
        assert math.isclose(t_stat, t_manual, rel_tol=1e-9), (col, t_stat, t_manual)

        rows.append({
            "test": col, "description": label, "n": n, "mean": mean,
            "median": median, "std": std, "share_positive": share_pos,
            "t_stat": t_stat, "p_value": p_value,
        })
    con.close()

    summary = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "summary.csv"
    summary.to_csv(out, index=False)

    print("=== Results (one-sample t-test, H0: mean = 0, two-sided) ===")
    show = summary.drop(columns="description").copy()
    for c in ("mean", "median", "std"):
        show[c] = show[c].map(lambda x: f"{x:+.4%}" if c != "std" else f"{x:.4%}")
    show["share_positive"] = show["share_positive"].map(lambda x: f"{x:.1%}")
    show["t_stat"] = show["t_stat"].map(lambda x: f"{x:.3f}")
    show["p_value"] = show["p_value"].map(lambda x: f"{x:.2e}")
    print(show.to_string(index=False))
    print(f"\nSaved -> {out.relative_to(RESULTS_DIR.parent)}")

    print("\n=== Inputs to recompute t by hand: t = mean / (sd / sqrt(n)) ===")
    for r in rows:
        se = r["std"] / math.sqrt(r["n"])
        print(f"\n{r['test']}  ({r['description']})")
        print(f"  n    = {r['n']}")
        print(f"  mean = {r['mean']:.8f}")
        print(f"  sd   = {r['std']:.8f}")
        print(f"  se   = sd / sqrt(n) = {r['std']:.8f} / {math.sqrt(r['n']):.6f} = {se:.8f}")
        print(f"  t    = mean / se = {r['mean']:.8f} / {se:.8f} = {r['mean'] / se:.4f}")
        print(f"  df   = n - 1 = {r['n'] - 1}")


if __name__ == "__main__":
    main()
