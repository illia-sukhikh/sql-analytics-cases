-- Case 1. Revenue dynamics
--
-- Business question: How did revenue, number of orders and average order value (AOV)
--                    develop month by month, and where are the spikes?
-- Expected output:   month | orders | revenue | aov | revenue_mom_pct
-- Definitions:       count delivered orders only (orders.order_status = 'delivered');
--                    revenue = SUM(order_items.price), without freight.
-- Period:            Jan 2017 - Aug 2018. Sep-Dec 2016 excluded: platform launch,
--                    a few hundred orders and no orders at all in Nov 2016.
-- Hints:             date_trunc('month', order_purchase_timestamp); one CTE per step;
--                    LAG() OVER (ORDER BY month) for month-over-month growth.
-- Chart:             line chart of revenue + bars of orders -> images/01_revenue.png

WITH order_revenue AS (            
    SELECT order_id,
           SUM(price) AS revenue
    FROM order_items
    GROUP BY order_id
),
monthly_base AS (                  
    SELECT date_trunc('month', o.order_purchase_timestamp)::date AS month,
           o.order_id,
           r.revenue
    FROM orders AS o
    JOIN order_revenue AS r ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
monthly_agg AS (                   
    SELECT month,
           COUNT(*)     AS orders,
           SUM(revenue) AS revenue,
           AVG(revenue) AS aov
    FROM monthly_base
    GROUP BY month
)
SELECT month,
       orders,
       ROUND(revenue::numeric, 0) AS revenue,
       ROUND(aov::numeric, 2)     AS aov,
       ROUND(((revenue - LAG(revenue) OVER w)
              / NULLIF(LAG(revenue) OVER w, 0) * 100)::numeric, 2) AS revenue_mom_pct
FROM monthly_agg
WINDOW w AS (ORDER BY month)
ORDER BY month;
