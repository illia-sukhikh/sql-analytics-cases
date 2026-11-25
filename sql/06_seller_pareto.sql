-- Case 6. Seller Pareto
--
-- Business question: Do 20% of sellers make 80% of the revenue,
--                    and how risky is that concentration?
-- Expected output:   seller_rank | seller_rank_pct | revenue | cum_revenue_share_pct (one row per seller)
--                    + top 10 sellers: sql/06b_top_sellers.sql
-- Definitions:       revenue = SUM(order_items.price) for delivered orders;
--                    late shipping = orders.order_delivered_carrier_date > order_items.shipping_limit_date.
-- Period:            delivered orders Jan 2017 - Aug 2018.
-- Hints:             ROW_NUMBER() and COUNT(*) OVER () for the rank percentile;
--                    SUM(...) OVER (ORDER BY revenue DESC) for the cumulative share.
-- Chart:             Pareto curve -> images/06_pareto.png

WITH seller_revenue AS (           -- step 1: revenue per seller, delivered orders of the period
    SELECT oi.seller_id,
           SUM(oi.price) AS revenue
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY oi.seller_id
)

SELECT ROW_NUMBER() OVER w                                                   AS seller_rank,
       ROUND(100.0 * ROW_NUMBER() OVER w / COUNT(*) OVER (), 2)              AS seller_rank_pct,
       ROUND(revenue::numeric, 2)                                            AS revenue,
       ROUND((100.0 * SUM(revenue) OVER w / SUM(revenue) OVER ())::numeric, 2) AS cum_revenue_share_pct
FROM seller_revenue
WINDOW w AS (ORDER BY revenue DESC, seller_id)
ORDER BY seller_rank;
