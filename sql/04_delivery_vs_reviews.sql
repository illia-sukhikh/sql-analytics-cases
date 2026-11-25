-- Case 4. Delivery quality vs. review score
--
-- Business question: How much does a late delivery lower the review score,
--                    and in which states is the problem worst?
-- Expected output:   delivery_status | orders | orders_share_pct | avg_review_score
--                    | share_1_2_stars_pct | share_of_all_1_2_star_reviews_pct
--                    + by state: sql/04b_delivery_by_state.sql
-- Definitions:       late = order_delivered_customer_date > order_estimated_delivery_date;
--                    delivered orders only; one review per order (deduplicate if needed).
-- Period:            delivered orders Jan 2017 - Aug 2018; orders without a delivery date
--                    or without a review are left out.
-- Notes:             dates are compared, not timestamps: the estimate has no time (00:00),
--                    so a delivery on the promised day would count as late by timestamp
--                    (1,291 such orders). When an order has several reviews, the latest is kept.
-- Hints:             CASE WHEN inside AVG / COUNT, or COUNT(*) FILTER (WHERE ...);
--                    JOIN orders -> order_reviews -> customers.
-- Chart:             average score on time vs. late -> images/04_delivery.png

WITH latest_review AS (            -- step 1: one review per order (547 orders have several): keep the latest
    SELECT order_id,
           review_score,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_answer_timestamp DESC, review_id) AS rn
    FROM order_reviews
),

deliveries AS (                    -- step 2: delivered orders with a review and the delay in days
    SELECT o.order_id,
           r.review_score,
           o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date AS days_late
    FROM orders AS o
    JOIN latest_review AS r ON r.order_id = o.order_id AND r.rn = 1
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),

bucketed AS (                      -- step 3: on time or how late
    SELECT *,
           CASE WHEN days_late <= 0  THEN 'On time'
                WHEN days_late <= 3  THEN '1-3 days late'
                WHEN days_late <= 7  THEN '4-7 days late'
                WHEN days_late <= 14 THEN '8-14 days late'
                ELSE                      '15+ days late'
           END AS delivery_status
    FROM deliveries
)

SELECT delivery_status,
       COUNT(*)                                                                      AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                            AS orders_share_pct,
       ROUND(AVG(review_score), 2)                                                   AS avg_review_score,
       ROUND(100.0 * COUNT(*) FILTER (WHERE review_score <= 2) / COUNT(*), 1)        AS share_1_2_stars_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE review_score <= 2)
             / SUM(COUNT(*) FILTER (WHERE review_score <= 2)) OVER (), 1)            AS share_of_all_1_2_star_reviews_pct
FROM bucketed
GROUP BY delivery_status
ORDER BY MIN(days_late);
