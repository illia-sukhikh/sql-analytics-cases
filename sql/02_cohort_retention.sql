-- Case 2. Cohort retention
--
-- Business question: What share of customers buys again 1, 2, 3 ... months
--                    after their first purchase?
-- Expected output:   cohort_month | months_since_first | customers | retention_pct
-- Definitions:       a customer = customers.customer_unique_id
--                    (customer_id changes with every order!);
--                    cohort = month of the customer's first delivered order.
-- Period:            cohorts Jan 2017 - Aug 2018 (first purchase searched over the full history);
--                    orders up to Aug 2018. 2016 excluded: three tiny cohorts (1, 262 and 1 customer).
-- Window:            first 12 months after the first purchase; cells after Aug 2018 are not observed.
-- Hints:             MIN() OVER (PARTITION BY customer) for the first order;
--                    month difference = (year * 12 + month) of the order minus the same for the cohort.
-- Note:              expect very low repeat rates; explaining why is part of the insight.
-- Chart:             heatmap cohort x month -> images/02_retention.png

WITH delivered_orders AS (         
    SELECT
        c.customer_unique_id,
        DATE_TRUNC('month', o.order_purchase_timestamp)::date AS order_month,
        (EXTRACT(YEAR  FROM o.order_purchase_timestamp)::int * 12
         + EXTRACT(MONTH FROM o.order_purchase_timestamp)::int) AS order_month_num
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp < '2018-09-01'
),

customer_first AS (                
    SELECT
        customer_unique_id,
        MIN(order_month_num) AS first_month_num,
        MIN(order_month)     AS cohort_month
    FROM delivered_orders
    GROUP BY customer_unique_id
),

customer_activity AS (            
    SELECT
        d.customer_unique_id,
        f.cohort_month,
        d.order_month_num - f.first_month_num AS months_since_first
    FROM delivered_orders AS d
    JOIN customer_first   AS f USING (customer_unique_id)
    WHERE d.order_month_num - f.first_month_num <= 12
),

cohort_size AS (                   
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customers
    FROM customer_first
    WHERE cohort_month >= '2017-01-01'
    GROUP BY cohort_month
),

retention AS (                     
    SELECT
        cohort_month,
        months_since_first,
        COUNT(DISTINCT customer_unique_id) AS customers
    FROM customer_activity
    GROUP BY cohort_month, months_since_first
),

grid AS (                          
    SELECT
        cs.cohort_month,
        cs.cohort_customers,
        m.months_since_first
    FROM cohort_size AS cs
    CROSS JOIN generate_series(0, 12) AS m(months_since_first)
    WHERE cs.cohort_month + make_interval(months => m.months_since_first) < '2018-09-01'
)

SELECT
    g.cohort_month,
    g.months_since_first,
    COALESCE(r.customers, 0) AS customers,
    ROUND(100.0 * COALESCE(r.customers, 0) / g.cohort_customers, 2) AS retention_pct
FROM grid AS g
LEFT JOIN retention AS r USING (cohort_month, months_since_first)
ORDER BY g.cohort_month, g.months_since_first;