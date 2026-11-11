"""Save three event-study charts to figures/.

  1_mean_ar_by_day.png       mean AR by relative day, 95% CI bars
  2_mean_abs_ar_by_day.png   mean |AR| by relative day
  3_day0_ar_histogram.png    histogram of day-0 ARs with a fitted normal curve

Run after src/build_events.py:  python src/charts.py
"""

import duckdb
import matplotlib

matplotlib.use("Agg")  # write files, no window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter
from scipy import stats

from config import DB_PATH, FIGURES_DIR

# Colors from the dataviz reference palette (light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES_1 = "#2a78d6"   # blue
SERIES_2 = "#eb6834"   # orange

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_SECONDARY,
    "axes.titlecolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 10.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "font.size": 10,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

AR_NOTE = "AR = stock return minus SPY return. 30 Dow stocks, 2023–2025."


def subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, fontsize=9.5,
            color=INK_SECONDARY, va="bottom")


def day_labels(ax, days) -> None:
    ax.set_xticks(days)
    # Use a true minus sign to match matplotlib's y-axis labels.
    ax.set_xticklabels([f"{d:+d}".replace("-", "−") if d else "0" for d in days])
    ax.set_xlabel("Trading days relative to the earnings reaction day (day 0)")
    ax.grid(axis="x", visible=False)


def by_day(con):
    return con.execute("""
        SELECT rel_day,
               COUNT(ar)         AS n,
               AVG(ar)           AS mean_ar,
               STDDEV_SAMP(ar)   AS sd_ar,
               AVG(ABS(ar))      AS mean_abs_ar
        FROM abnormal_returns
        GROUP BY rel_day
        ORDER BY rel_day
    """).df()


def chart_mean_ar(df, path) -> None:
    se = df["sd_ar"] / np.sqrt(df["n"])
    half_ci = stats.t.ppf(0.975, df["n"] - 1) * se

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.axhline(0, color=INK_SECONDARY, linewidth=1)
    ax.errorbar(df["rel_day"], df["mean_ar"], yerr=half_ci, fmt="o",
                color=SERIES_1, ecolor=SERIES_1, elinewidth=2, capsize=5,
                capthick=2, markersize=8, markeredgecolor=SURFACE,
                markeredgewidth=2)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=1))
    ax.set_ylabel("Mean abnormal return")
    day_labels(ax, df["rel_day"])
    ax.set_title("Mean abnormal return around earnings announcements", pad=24)
    subtitle(ax, f"Dots: mean across {int(df['n'].iloc[0])} events. "
                 f"Bars: 95% confidence interval. {AR_NOTE}")
    fig.savefig(path)
    plt.close(fig)


def chart_mean_abs_ar(df, path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(df["rel_day"], df["mean_abs_ar"], width=0.7, color=SERIES_1)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=1))
    ax.set_ylabel("Mean absolute abnormal return")
    day_labels(ax, df["rel_day"])
    ax.set_title("Mean absolute abnormal return around earnings announcements",
                 pad=24)
    subtitle(ax, f"Mean of |AR| across {int(df['n'].iloc[0])} events. {AR_NOTE}")
    fig.savefig(path)
    plt.close(fig)


def chart_histogram(con, path) -> None:
    ar = con.execute(
        "SELECT ar FROM abnormal_returns WHERE rel_day = 0 AND ar IS NOT NULL"
    ).df()["ar"].to_numpy()
    n, mean, sd = len(ar), ar.mean(), ar.std(ddof=1)

    bin_width = 0.01  # 1 percentage point
    lo = np.floor(ar.min() / bin_width) * bin_width
    hi = np.ceil(ar.max() / bin_width) * bin_width
    bins = np.arange(lo, hi + bin_width / 2, bin_width)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(ar, bins=bins, color=SERIES_1, edgecolor=SURFACE, linewidth=1.5,
            label="Day-0 abnormal returns")
    # Normal curve scaled from density to counts per bin.
    x = np.linspace(lo, hi, 400)
    ax.plot(x, stats.norm.pdf(x, mean, sd) * n * bin_width, color=SERIES_2,
            linewidth=2, label="Normal curve, same mean and SD")
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel("Day-0 abnormal return (bins of 1 percentage point)")
    ax.set_ylabel("Number of events")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, loc="upper left")
    ax.set_title("Distribution of day-0 abnormal returns", pad=24)
    subtitle(ax, f"n = {n} events, mean = {mean:+.2%}, SD = {sd:.2%}. {AR_NOTE}")
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = by_day(con)

    outputs = {
        "1_mean_ar_by_day.png": lambda p: chart_mean_ar(df, p),
        "2_mean_abs_ar_by_day.png": lambda p: chart_mean_abs_ar(df, p),
        "3_day0_ar_histogram.png": lambda p: chart_histogram(con, p),
    }
    for name, draw in outputs.items():
        path = FIGURES_DIR / name
        draw(path)
        print(f"saved -> figures/{name}")
    con.close()


if __name__ == "__main__":
    main()
