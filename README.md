# SQL Analytics Cases: Olist E-Commerce

> Six business questions answered with PostgreSQL on ~100k real e-commerce orders: revenue dynamics, retention, RFM, delivery quality, assortment and sellers.

## Business context

Olist is a Brazilian platform that helps small merchants sell on large online marketplaces. The public dataset covers ~100k orders from 2016 to 2018, with payments, deliveries, reviews, products and sellers.

I analyze it the way I would for a commercial team: every case starts with a business question and ends with a recommendation.

## Cases

| # | Business question | Techniques | Query | Status |
| --- | --- | --- | --- | --- |
| 1 | How did revenue, orders and average order value develop month by month? | CTE, `date_trunc`, `LAG` | [01](sql/01_revenue_dynamics.sql) | to do |
| 2 | Do customers come back after their first purchase? | Cohorts, retention matrix | [02](sql/02_cohort_retention.sql) | to do |
| 3 | Which customer segments generate the revenue? | RFM, `NTILE` | [03](sql/03_rfm_segmentation.sql) | to do |
| 4 | How much does a late delivery hurt the review score? | Joins, conditional aggregation | [04](sql/04_delivery_vs_reviews.sql) | to do |
| 5 | Which categories form the revenue core, and which are unstable? | ABC/XYZ, cumulative share, coefficient of variation | [05](sql/05_abc_xyz_categories.sql) | to do |
| 6 | Do 20% of sellers make 80% of the revenue? | Window functions, Pareto | [06](sql/06_seller_pareto.sql) | to do |

## Results

_Fill in after each case: one chart, two or three sentences with numbers, one recommendation._

### 1. Revenue dynamics

![Revenue dynamics](images/01_revenue.png)

**Insight:** …

**Recommendation:** …

## Data

Brazilian E-Commerce Public Dataset by Olist (Kaggle): 9 CSV files, ~100k orders, 2016–2018. The raw files are not stored in this repository, see [data/README.md](data/README.md).

## How to run

1. Install PostgreSQL and create a database called `olist`.
2. Download the dataset and put the CSV files into `data/raw/`.
3. Copy `.env.example` to `.env` and set `DATABASE_URL`.
4. Load the data:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python scripts/load_olist.py
```

5. Run `sql/00_check_load.sql` to check the row counts, then the case queries.

## Project structure

```
sql-analytics-cases/
├── data/
│   └── README.md          # how to download the dataset
├── images/                # charts used in this README
├── notebooks/             # charts and exploration
├── scripts/
│   └── load_olist.py      # loads the CSV files into PostgreSQL
├── sql/
│   ├── 00_check_load.sql
│   └── 01–06_*.sql        # one file per business case
├── .env.example
├── requirements.txt
└── README.md
```

## Author

Illia Sukhikh · Data Analyst · [LinkedIn](https://www.linkedin.com/in/illia-sukhikh) · illia.sukhikh.data@gmail.com
