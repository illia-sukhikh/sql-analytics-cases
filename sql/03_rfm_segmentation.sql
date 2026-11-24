-- Case 3. RFM segmentation
--
-- Business question: Which customer segments generate most of the revenue,
--                    and whom should marketing target?
-- Expected output:   segment | customers | customers_share_pct | revenue | revenue_share_pct | avg_monetary
--                    (+ avg_recency_days and avg_frequency to show that frequency is ~1 everywhere)
-- Definitions:       reference date = latest order date + 1 day; recency in days;
--                    frequency = number of delivered orders per customer_unique_id;
--                    monetary = SUM(order_payments.payment_value).
-- Period:            delivered orders Jan 2017 - Aug 2018 (same as cases 1 and 2);
--                    reference date = 2018-08-30.
-- Segments:          R and M scores from NTILE(5), 5 = best; frequency is 1 for 97% of customers,
--                    so it is not used. VIP: R 4-5 and M 4-5; New: R 4-5, M 1-3;
--                    Need attention: R 3; Sleeping: R 1-2, M 4-5; Lost: R 1-2, M 1-3.
-- Hints:             NTILE(5) for R, F and M scores. Frequency is almost always 1 here,
--                    so consider an R + M segmentation and explain the choice in the README.
-- Chart:             bar chart of revenue share by segment -> images/03_rfm.png

WITH delivered AS (                
    SELECT c.customer_unique_id,
           o.order_id,
           o.order_purchase_timestamp
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),

order_payment AS (                 
    SELECT order_id,
           SUM(payment_value) AS paid
    FROM order_payments
    GROUP BY order_id
),

reference AS (                     
    SELECT MAX(order_purchase_timestamp)::date + 1 AS reference_date
    FROM delivered
),

rfm AS (                           
    SELECT d.customer_unique_id,
           r.reference_date - MAX(d.order_purchase_timestamp)::date AS recency_days,
           COUNT(*)                                                 AS frequency,
           COALESCE(SUM(p.paid), 0)                                 AS monetary
    FROM delivered AS d
    CROSS JOIN reference AS r
    LEFT JOIN order_payment AS p ON p.order_id = d.order_id
    GROUP BY d.customer_unique_id, r.reference_date
),

scored AS (                        
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC, customer_unique_id) AS r_score,
           NTILE(5) OVER (ORDER BY monetary,          customer_unique_id) AS m_score
    FROM rfm
),

segmented AS (                     
    SELECT *,
           CASE
               WHEN r_score >= 4 AND m_score >= 4 THEN 'VIP'
               WHEN r_score >= 4                  THEN 'New'
               WHEN r_score  = 3                  THEN 'Need attention'
               WHEN m_score >= 4                  THEN 'Sleeping'
               ELSE                                    'Lost'
           END AS segment
    FROM scored
)

SELECT segment,
       COUNT(*)                                                                 AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                       AS customers_share_pct,
       ROUND(SUM(monetary)::numeric, 0)                                         AS revenue,
       ROUND((100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER ())::numeric, 1)  AS revenue_share_pct,
       ROUND(AVG(monetary)::numeric, 2)                                         AS avg_monetary,
       ROUND(AVG(recency_days), 0)                                              AS avg_recency_days,
       ROUND(AVG(frequency), 2)                                                 AS avg_frequency
FROM segmented
GROUP BY segment
ORDER BY revenue DESC;
