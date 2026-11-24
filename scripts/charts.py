"""Build the README charts from the case queries.

Usage (from the project root, with the virtual environment active):
    python scripts/charts.py

Every chart runs the SQL file of its case, so the picture always matches the published query.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from matplotlib.ticker import FuncFormatter
from sqlalchemy import create_engine, text

plt.switch_backend("agg")  # files only, no windows

PROJECT_DIR = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_DIR / "sql"
IMG_DIR = PROJECT_DIR / "images"

INK = "#1F2933"      # titles
MUTED = "#616E7C"    # subtitles, axes, notes
GRID = "#E4E7EB"     # grid lines
BARS = "#CBD2D9"     # context series
ACCENT = "#2563EB"   # the main metric

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans"],  # Segoe UI on Windows, DejaVu Sans elsewhere
    "font.size": 10,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
})


def run_sql(engine, file_name: str, date_cols: list[str] | None = None) -> pd.DataFrame:
    """Run a case query from sql/ and return the result as a DataFrame."""
    query = (SQL_DIR / file_name).read_text(encoding="utf-8-sig")  # -sig: also reads files saved with a BOM
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, parse_dates=date_cols)


def short_money(value: float, _pos=None) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"  # 1M, 1.25M, 1.5M
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def clean_axes(*axes) -> None:
    for ax in axes:
        for side in ("top", "left", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(length=0)


def add_titles(fig, title: str, subtitle: str, source: str) -> None:
    fig.text(0.02, 0.96, title, fontsize=14, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.905, subtitle, fontsize=10, color=MUTED, va="top")
    fig.text(0.02, 0.02, source, fontsize=8, color=MUTED, va="bottom")


def save(fig, file_name: str) -> Path:
    path = IMG_DIR / file_name
    fig.savefig(path, dpi=200, facecolor="white")  # white, not transparent: readable in GitHub dark mode
    plt.close(fig)
    return path


# ---------- Case 1. Revenue dynamics ----------
# Replace with your finding once you have looked at the numbers.
TITLE_01 = "Revenue grew 8× in a year, then plateaued at about BRL 0.9M a month"
# Optional: mark the spike you found in the daily drill-down, e.g. ("2017-11-01", "your label").
SPIKE_01: tuple[str, str] | None = ("2017-11-01", "Black Friday, 24 Nov: 1,147 orders in one day")


def chart_revenue(engine) -> Path:
    df = run_sql(engine, "01_revenue_dynamics.sql", date_cols=["month"])
    df[["orders", "revenue"]] = df[["orders", "revenue"]].astype(float)

    fig, ax_rev = plt.subplots(figsize=(10, 5.6))
    ax_orders = ax_rev.twinx()
    ax_rev.set_zorder(ax_orders.get_zorder() + 1)  # line above the bars
    ax_rev.patch.set_visible(False)

    bars = ax_orders.bar(df["month"], df["orders"], width=20, color=BARS, label="Orders (right axis)")
    (line,) = ax_rev.plot(df["month"], df["revenue"], color=ACCENT, linewidth=2.5,
                          marker="o", markersize=4, label="Revenue, BRL (left axis)")

    ax_rev.set_ylim(bottom=0)      # both axes start at zero, otherwise the chart exaggerates
    ax_orders.set_ylim(bottom=0)
    ax_rev.yaxis.set_major_formatter(FuncFormatter(short_money))
    ax_orders.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax_rev.set_ylabel("Revenue, BRL")
    ax_orders.set_ylabel("Orders")
    ax_rev.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax_rev.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax_rev.grid(axis="y", color=GRID, linewidth=0.8)
    clean_axes(ax_rev, ax_orders)

    if SPIKE_01:
        month, label = SPIKE_01
        point = df.loc[df["month"] == pd.Timestamp(month)].iloc[0]
        ax_rev.annotate(label, xy=(point["month"], point["revenue"]), xytext=(-120, 14),
                        textcoords="offset points", color=INK, fontsize=9,
                        arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8})

    ax_rev.legend(handles=[line, bars], loc="upper left", frameon=False)
    add_titles(fig, TITLE_01,
               "Delivered orders by purchase month · revenue = item price, excl. freight",
               "Source: Olist public dataset (Kaggle) · query: sql/01_revenue_dynamics.sql")
    fig.subplots_adjust(left=0.08, right=0.92, top=0.83, bottom=0.12)
    return save(fig, "01_revenue.png")


# ---------- Case 2. Cohort retention ----------
TITLE_02 = "Fewer than 1% of customers buy again in any month after the first"


def chart_retention(engine) -> Path:
    df = run_sql(engine, "02_cohort_retention.sql", date_cols=["cohort_month"])
    df["retention_pct"] = df["retention_pct"].astype(float)

    sizes = df.loc[df["months_since_first"] == 0].set_index("cohort_month")["customers"]
    grid = (df.loc[df["months_since_first"] > 0]
              .pivot(index="cohort_month", columns="months_since_first", values="retention_pct")
              .reindex(index=sizes.index, columns=range(1, 13)))  # empty cell = not observed yet
    top_value = grid.max().max()

    fig, ax = plt.subplots(figsize=(10, 7.6))
    cmap = plt.get_cmap("Blues").with_extremes(bad="white")
    heat = ax.imshow(grid.to_numpy(dtype=float), cmap=cmap, vmin=0, vmax=top_value, aspect="auto")

    for row, cohort in enumerate(grid.index):          # the value in every observed cell
        for col, month in enumerate(grid.columns):
            value = grid.loc[cohort, month]
            if pd.notna(value):
                ax.text(col, row, f"{value:.2f}", ha="center", va="center", fontsize=7.5,
                        color="white" if value > 0.6 * top_value else INK)

    ax.set_xticks(range(len(grid.columns)), labels=grid.columns)
    ax.set_yticks(range(len(grid.index)),
                  labels=[f"{month:%b %Y} · {sizes[month]:,}" for month in grid.index])
    ax.set_xticks([x + 0.5 for x in range(len(grid.columns) - 1)], minor=True)
    ax.set_yticks([y + 0.5 for y in range(len(grid.index) - 1)], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)   # white lines between the cells
    ax.tick_params(which="both", length=0)
    ax.set_xlabel("Months after the first purchase")
    ax.set_ylabel("Cohort (month of the first purchase) · customers")
    for spine in ax.spines.values():
        spine.set_visible(False)

    bar = fig.colorbar(heat, ax=ax, shrink=0.6, pad=0.02)
    bar.set_label("Bought again, % of the cohort", color=MUTED)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0)

    add_titles(fig, TITLE_02,
               "Share of each cohort with a delivered order N months later · blank = not observed yet",
               "Source: Olist public dataset (Kaggle) · query: sql/02_cohort_retention.sql")
    fig.subplots_adjust(left=0.2, right=0.98, top=0.86, bottom=0.1)
    return save(fig, "02_retention.png")

# ---------- Case 3. RFM segmentation ----------
TITLE_03 = "One third of customers (VIP and Sleeping) bring 60% of all payments"
SEGMENT_NOTES_03 = {                   # what each segment means, shown under its name
    "VIP": "recent, high spend",
    "Sleeping": "long ago, high spend",
    "Need attention": "in between",
    "New": "recent, low spend",
    "Lost": "long ago, low spend",
}


def chart_rfm(engine) -> Path:
    df = run_sql(engine, "03_rfm_segmentation.sql")
    shares = ["customers_share_pct", "revenue_share_pct"]
    df[shares] = df[shares].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)          # the largest share of payments on top

    fig, ax = plt.subplots(figsize=(10, 5.8))
    rows, height = list(range(len(df))), 0.38
    ax.barh([y + height / 2 for y in rows], df["customers_share_pct"], height=height,
            color=BARS, label="Share of customers")
    ax.barh([y - height / 2 for y in rows], df["revenue_share_pct"], height=height,
            color=ACCENT, label="Share of payments")
    for y, (customers, payments) in enumerate(zip(df["customers_share_pct"], df["revenue_share_pct"])):
        ax.text(customers + 0.5, y + height / 2, f"{customers:.1f}%", va="center", fontsize=9, color=MUTED)
        ax.text(payments + 0.5, y - height / 2, f"{payments:.1f}%", va="center", fontsize=9,
                color=INK, fontweight="bold")

    ax.set_yticks(rows, labels=[f"{name}\n{SEGMENT_NOTES_03.get(name, '')}" for name in df["segment"]])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(0, df[shares].to_numpy().max() * 1.15)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    clean_axes(ax)
    ax.legend(loc="lower right", frameon=False)

    add_titles(fig, TITLE_03,
               "Share of customers and of payments by RFM segment (recency × monetary, NTILE(5))",
               "Source: Olist public dataset (Kaggle) · query: sql/03_rfm_segmentation.sql")
    fig.subplots_adjust(left=0.2, right=0.95, top=0.83, bottom=0.12)
    return save(fig, "03_rfm.png")


CHARTS = [chart_revenue, chart_retention, chart_rfm]  # add one function per case as you go


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
        return 1
    IMG_DIR.mkdir(exist_ok=True)
    engine = create_engine(database_url)
    for build in CHARTS:
        print(f"saved {build(engine).relative_to(PROJECT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
