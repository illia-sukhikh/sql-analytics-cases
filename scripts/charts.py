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


# ---------- Case 4. Delivery quality vs. review score ----------
TITLE_04 = "A delay of just 1-3 days costs a full review star"


def chart_delivery(engine) -> Path:
    df = run_sql(engine, "04_delivery_vs_reviews.sql")
    cols = ["orders_share_pct", "avg_review_score", "share_1_2_stars_pct"]
    df[cols] = df[cols].astype(float)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    colors = [BARS if status == "On time" else ACCENT for status in df["delivery_status"]]
    ax.bar(range(len(df)), df["avg_review_score"], width=0.6, color=colors)
    for x, (score, low) in enumerate(zip(df["avg_review_score"], df["share_1_2_stars_pct"])):
        ax.text(x, score + 0.12, f"{score:.2f}", ha="center", fontsize=12, fontweight="bold", color=INK)
        ax.text(x, score + 0.45, f"1-2 stars: {low:.0f}%", ha="center", fontsize=9, color=MUTED)

    ax.set_xticks(range(len(df)), labels=[f"{status}\n{share:.1f}% of orders"
                                          for status, share in zip(df["delivery_status"], df["orders_share_pct"])])
    ax.set_ylim(0, 5.3)
    ax.set_ylabel("Average review score (1-5)")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    clean_axes(ax)

    add_titles(fig, TITLE_04,
               "Average review score by delivery delay · late = delivered after the promised day",
               "Source: Olist public dataset (Kaggle) · query: sql/04_delivery_vs_reviews.sql")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.15)
    return save(fig, "04_delivery.png")


# ---------- Case 5. ABC/XYZ analysis of product categories ----------
TITLE_05 = "Nine stable categories (A + X) bring 55% of revenue"


def chart_abc_xyz(engine) -> Path:
    df = run_sql(engine, "05_abc_xyz_categories.sql")
    df["revenue"] = df["revenue"].astype(float)
    cells = df.groupby(["abc", "xyz"]).agg(categories=("category", "count"), revenue=("revenue", "sum"))
    share = (100 * cells["revenue"] / df["revenue"].sum()).unstack(fill_value=0)
    share = share.reindex(index=["A", "B", "C"], columns=["X", "Y", "Z"], fill_value=0)
    counts = cells["categories"].unstack(fill_value=0).reindex(index=["A", "B", "C"], columns=["X", "Y", "Z"], fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.imshow(share.to_numpy(dtype=float), cmap="Blues", vmin=0, vmax=share.to_numpy().max(), aspect="auto")
    for row, abc in enumerate(share.index):
        for col, xyz in enumerate(share.columns):
            value, n = share.loc[abc, xyz], counts.loc[abc, xyz]
            color = "white" if value > 0.55 * share.to_numpy().max() else INK
            ax.text(col, row - 0.08, f"{value:.1f}%", ha="center", va="center", fontsize=16, fontweight="bold", color=color)
            ax.text(col, row + 0.22, f"{n} categor{'y' if n == 1 else 'ies'}", ha="center", va="center",
                    fontsize=9.5, color=color)

    ax.set_xticks(range(3), labels=["X\nstable, CV < 0.25", "Y\nCV 0.25-0.5", "Z\nunstable, CV >= 0.5"])
    ax.set_yticks(range(3), labels=["A\ntop 80% of revenue", "B\nnext 15%", "C\nlast 5%"])
    ax.xaxis.tick_top()
    ax.set_xticks([0.5, 1.5], minor=True)
    ax.set_yticks([0.5, 1.5], minor=True)
    ax.grid(which="minor", color="white", linewidth=3)
    ax.tick_params(which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    add_titles(fig, TITLE_05,
               "Share of revenue by ABC class (revenue) and XYZ class (monthly demand variation) · Jan-Aug 2018",
               "Source: Olist public dataset (Kaggle) · query: sql/05_abc_xyz_categories.sql")
    fig.subplots_adjust(left=0.2, right=0.97, top=0.76, bottom=0.08)
    return save(fig, "05_abc_xyz.png")


# ---------- Case 6. Seller Pareto ----------
def chart_pareto(engine) -> Path:
    df = run_sql(engine, "06_seller_pareto.sql")
    df[["seller_rank_pct", "cum_revenue_share_pct"]] = df[["seller_rank_pct", "cum_revenue_share_pct"]].astype(float)
    at_20 = df.loc[df["seller_rank_pct"] <= 20].iloc[-1]          # the point where 20% of sellers are counted
    half = df.loc[df["cum_revenue_share_pct"] >= 50].iloc[0]       # the first seller that reaches 50%
    title = (f"20% of sellers make {at_20['cum_revenue_share_pct']:.0f}% of revenue, "
             f"and {int(half['seller_rank'])} sellers make half of it")

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot([0, 100], [0, 100], color=GRID, linewidth=1.2, linestyle="--")
    ax.fill_between(df["seller_rank_pct"], df["cum_revenue_share_pct"], color=ACCENT, alpha=0.08)
    ax.plot(df["seller_rank_pct"], df["cum_revenue_share_pct"], color=ACCENT, linewidth=2.5)
    for point, label, offset in (
            (at_20, f"{at_20['seller_rank_pct']:.0f}% of sellers → {at_20['cum_revenue_share_pct']:.1f}% of revenue", (14, -28)),
            (half, f"{int(half['seller_rank'])} sellers ({half['seller_rank_pct']:.1f}%) → 50% of revenue", (16, -14))):
        ax.scatter(point["seller_rank_pct"], point["cum_revenue_share_pct"], color=ACCENT, s=36, zorder=3)
        ax.annotate(label, xy=(point["seller_rank_pct"], point["cum_revenue_share_pct"]), xytext=offset,
                    textcoords="offset points", fontsize=10, color=INK)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Share of sellers, largest first")
    ax.set_ylabel("Cumulative share of revenue")
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    clean_axes(ax)

    add_titles(fig, title,
               f"Sellers ranked by revenue · {len(df):,} sellers, delivered orders Jan 2017 - Aug 2018"
               " · dashed = all sellers equal",
               "Source: Olist public dataset (Kaggle) · query: sql/06_seller_pareto.sql")
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.14)
    return save(fig, "06_pareto.png")


CHARTS = [chart_revenue, chart_retention, chart_rfm,
          chart_delivery, chart_abc_xyz, chart_pareto]  # one function per case


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
