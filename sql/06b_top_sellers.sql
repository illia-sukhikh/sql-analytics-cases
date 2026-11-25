-- Case 6b. Top 10 sellers
--
-- Business question: Who are the largest sellers, and how reliable is their shipping?
-- Expected output:   seller_rank | seller_id | seller_state | revenue | revenue_share_pct
--                    | orders | late_shipping_pct
-- Definitions:       revenue = SUM(order_items.price) for delivered orders; revenue share of all sellers;
--                    late shipping = orders.order_delivered_carrier_date > order_items.shipping_limit_date,
--                    share of the seller's items with a carrier date.
-- Period:            delivered orders Jan 2017 - Aug 2018.

WITH items AS (                    -- step 1: delivered items of the period
    SELECT oi.seller_id,
           oi.order_id,
           oi.price,
           oi.shipping_limit_date,
           o.order_delivered_carrier_date
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),

per_seller AS (                    -- step 2: one row per seller
    SELECT seller_id,
           SUM(price)               AS revenue,
           COUNT(DISTINCT order_id) AS orders,
           100.0 * COUNT(*) FILTER (WHERE order_delivered_carrier_date > shipping_limit_date)
                 / NULLIF(COUNT(*) FILTER (WHERE order_delivered_carrier_date IS NOT NULL), 0) AS late_shipping_pct
    FROM items
    GROUP BY seller_id
),

ranked AS (                        -- step 3: rank and share of all sellers' revenue
    SELECT ps.*,
           ROW_NUMBER() OVER (ORDER BY ps.revenue DESC, ps.seller_id) AS seller_rank,
           100.0 * ps.revenue / SUM(ps.revenue) OVER ()               AS revenue_share_pct
    FROM per_seller AS ps
)

SELECT r.seller_rank,
       r.seller_id,
       s.seller_state,
       ROUND(r.revenue::numeric, 0)           AS revenue,
       ROUND(r.revenue_share_pct::numeric, 2) AS revenue_share_pct,
       r.orders,
       ROUND(r.late_shipping_pct::numeric, 1) AS late_shipping_pct
FROM ranked AS r
JOIN sellers AS s ON s.seller_id = r.seller_id
WHERE r.seller_rank <= 10
ORDER BY r.seller_rank;
