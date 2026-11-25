-- Case 4b. Late deliveries by customer state
--
-- Business question: In which states is the late-delivery problem worst?
-- Expected output:   customer_state | orders | late_pct | avg_review_score | avg_delivery_days
-- Definitions:       the same as in 04_delivery_vs_reviews.sql; late = delivered after the
--                    estimated day; delivery days = from purchase to delivery.
-- Period:            delivered orders Jan 2017 - Aug 2018; states with at least 300 orders.

WITH latest_review AS (            -- step 1: one review per order, the latest
    SELECT order_id,
           review_score,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_answer_timestamp DESC, review_id) AS rn
    FROM order_reviews
),

deliveries AS (                    -- step 2: delivered orders with the customer's state
    SELECT c.customer_state,
           r.review_score,
           o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date AS is_late,
           o.order_delivered_customer_date::date - o.order_purchase_timestamp::date     AS delivery_days
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    JOIN latest_review AS r ON r.order_id = o.order_id AND r.rn = 1
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)

SELECT customer_state,
       COUNT(*)                                                   AS orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_late) / COUNT(*), 1) AS late_pct,
       ROUND(AVG(review_score), 2)                                AS avg_review_score,
       ROUND(AVG(delivery_days), 1)                               AS avg_delivery_days
FROM deliveries
GROUP BY customer_state
HAVING COUNT(*) >= 300
ORDER BY late_pct DESC;
