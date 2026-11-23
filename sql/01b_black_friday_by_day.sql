-- Case 1, drill-down. November 2017 by day
--
-- Business question: Which days made November 2017 the record month?
-- Expected output:   purchase_day | weekday | orders | x_median_day
-- Definitions:       delivered orders only; x_median_day = orders of the day
--                    divided by the median day of November 2017.
-- Note:              ">= ... AND < ..." keeps every order of 30 November;
--                    BETWEEN '2017-11-01' AND '2017-11-30' would lose orders after 00:00 on the 30th.

WITH daily AS (                    -- step 1: delivered orders per day of November 2017
    SELECT o.order_purchase_timestamp::date AS purchase_day,
           COUNT(*)                         AS orders
    FROM orders AS o
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-11-01'
      AND o.order_purchase_timestamp <  '2017-12-01'
    GROUP BY purchase_day
),
typical AS (                       -- step 2: a typical day = the median day of the month
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY orders) AS median_orders
    FROM daily
)
SELECT d.purchase_day,
       to_char(d.purchase_day, 'Dy')                   AS weekday,
       d.orders,
       ROUND((d.orders / t.median_orders)::numeric, 1) AS x_median_day
FROM daily AS d
CROSS JOIN typical AS t
ORDER BY d.orders DESC
LIMIT 5;
