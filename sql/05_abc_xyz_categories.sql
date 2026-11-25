-- Case 5. ABC/XYZ analysis of product categories
--
-- Business question: Which categories form the revenue core (A),
--                    and which have unstable demand (Z)?
-- Expected output:   category | revenue | revenue_share_pct | cum_share_pct | abc | cv | xyz
-- Definitions:       ABC by cumulative revenue share: A <= 80%, B <= 95%, C = the rest;
--                    XYZ by coefficient of variation (CV) of monthly revenue:
--                    X < 0.25, Y < 0.5, Z >= 0.5 (state your thresholds in the README).
-- Period:            delivered orders Jan - Aug 2018, the plateau after the 2017 growth (case 1).
--                    Over the full period 60 of 74 categories would be Z only because the
--                    business grew 8x, not because their demand is unstable.
-- Notes:             months without sales count as 0 in the CV; two categories without an
--                    English name keep the Portuguese one; products without a category
--                    are grouped as '(no category)'.
-- Hints:             English category names via category_translation;
--                    SUM(...) OVER (ORDER BY revenue DESC) for the cumulative share;
--                    STDDEV_POP() / AVG() of monthly revenue per category for the CV.
-- Chart:             ABC x XYZ matrix with revenue -> images/05_abc_xyz.png

WITH sales AS (                    -- step 1: revenue per category and month, delivered orders of Jan-Aug 2018
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, '(no category)') AS category,
           date_trunc('month', o.order_purchase_timestamp)::date                             AS month,
           SUM(oi.price)                                                                      AS revenue
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    LEFT JOIN category_translation AS t ON t.product_category_name = p.product_category_name
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2018-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY 1, 2
),

monthly AS (                       -- step 2: every category x every month, months without sales = 0
    SELECT c.category,
           m.month::date                AS month,
           COALESCE(s.revenue, 0)       AS revenue
    FROM (SELECT DISTINCT category FROM sales) AS c
    CROSS JOIN generate_series(DATE '2018-01-01', DATE '2018-08-01', INTERVAL '1 month') AS m(month)
    LEFT JOIN sales AS s ON s.category = c.category AND s.month = m.month::date
),

per_category AS (                  -- step 3: total revenue and coefficient of variation of monthly revenue
    SELECT category,
           SUM(revenue)                                AS revenue,
           STDDEV_POP(revenue) / NULLIF(AVG(revenue), 0) AS cv
    FROM monthly
    GROUP BY category
),

ranked AS (                        -- step 4: share and cumulative share, largest category first
    SELECT category,
           revenue,
           cv,
           100.0 * revenue / SUM(revenue) OVER ()                                  AS revenue_share_pct,
           100.0 * SUM(revenue) OVER (ORDER BY revenue DESC, category) / SUM(revenue) OVER () AS cum_share_pct
    FROM per_category
)

SELECT category,
       ROUND(revenue::numeric, 0)            AS revenue,
       ROUND(revenue_share_pct::numeric, 2)  AS revenue_share_pct,
       ROUND(cum_share_pct::numeric, 2)      AS cum_share_pct,
       CASE WHEN cum_share_pct <= 80 THEN 'A'
            WHEN cum_share_pct <= 95 THEN 'B'
            ELSE 'C' END                     AS abc,
       ROUND(cv::numeric, 2)                 AS cv,
       CASE WHEN cv < 0.25 THEN 'X'
            WHEN cv < 0.5  THEN 'Y'
            ELSE 'Z' END                     AS xyz
FROM ranked
ORDER BY revenue DESC;
