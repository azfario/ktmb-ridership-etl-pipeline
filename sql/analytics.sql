-- Summarize reported ridership for each date.
CREATE OR REPLACE VIEW mart_daily_ridership AS
SELECT
    date,
    SUM(ridership) AS total_ridership,
    COUNT(DISTINCT service) AS service_count
FROM ktmb_ridership
GROUP BY date;

-- Display the latest 10 dates.
SELECT
    date,
    total_ridership,
    service_count
FROM mart_daily_ridership
ORDER BY date desc
LIMIT 10;

-- Summarize all available records for each service.
CREATE OR REPLACE VIEW mart_service_performance AS
SELECT
    service,
    MIN(date) AS first_date,
    MAX(date) AS latest_date,
    COUNT(*) AS days_reported,
    SUM(ridership) AS total_ridership,
    ROUND(AVG(ridership), 2) AS avg_daily_ridership
FROM ktmb_ridership
GROUP BY service;

-- Display services ordered by historical total.
SELECT
    service,
    first_date,
    latest_date,
    days_reported,
    total_ridership,
    avg_daily_ridership
FROM mart_service_performance
ORDER BY total_ridership DESC, service;

-- Calculate averages over complete calendar-day windows.
CREATE OR REPLACE VIEW mart_daily_ridership_trends AS
SELECT
    date,
    total_ridership,
    service_count,
    CASE
        WHEN COUNT(*) OVER seven_days = 7
        THEN ROUND(AVG(total_ridership) OVER seven_days, 2)
    END AS moving_avg_7d,
    CASE
        WHEN COUNT(*) OVER thirty_days = 30
        THEN ROUND(AVG(total_ridership) OVER thirty_days, 2)
    END AS moving_avg_30d
FROM mart_daily_ridership
WINDOW
    seven_days AS (
        ORDER BY date
        RANGE BETWEEN INTERVAL '6 days' PRECEDING
                  AND CURRENT ROW
    ),
    thirty_days AS (
        ORDER BY date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING
                  AND CURRENT ROW
    );

-- Display the latest 10 dates and their averages.
SELECT
    date,
    total_ridership,
    service_count,
    moving_avg_7d,
    moving_avg_30d
FROM mart_daily_ridership_trends
ORDER BY date DESC
LIMIT 10;

-- Compare weekdays and weekends with all five services present.
CREATE OR REPLACE VIEW mart_weekday_weekend_ridership AS
WITH classified_days AS (
    SELECT
        date,
        total_ridership,
        CASE
            WHEN EXTRACT(ISODOW FROM date) IN (6, 7)
                THEN 'Weekend'
            ELSE 'Weekday'
        END AS day_type
    FROM mart_daily_ridership
    WHERE service_count = 5
)
SELECT
    day_type,
    MIN(date) AS first_date,
    MAX(date) AS latest_date,
    COUNT(*) AS days_reported,
    SUM(total_ridership) AS total_ridership,
    ROUND(AVG(total_ridership), 2) AS avg_daily_ridership
FROM classified_days
GROUP BY day_type;

-- Display the comparison.
SELECT
    day_type,
    first_date,
    latest_date,
    days_reported,
    total_ridership,
    avg_daily_ridership
FROM mart_weekday_weekend_ridership
ORDER BY day_type;

-- Summarize each month and check reporting coverage.
CREATE OR REPLACE VIEW mart_monthly_ridership AS
WITH monthly_totals AS (
    SELECT
        DATE_TRUNC('month', date)::date AS month_start,
        COUNT(*) AS days_reported,
        COUNT(*) FILTER (
            WHERE service_count = 5
        ) AS full_service_days,
        SUM(total_ridership) AS total_ridership
    FROM mart_daily_ridership
    GROUP BY DATE_TRUNC('month', date)::date
),
monthly_status AS (
    SELECT
        *,
        (month_start + INTERVAL '1 month')::date
            - month_start AS days_in_month,
        (
            days_reported =
                (month_start + INTERVAL '1 month')::date
                - month_start
            AND full_service_days = days_reported
        ) AS is_complete
    FROM monthly_totals
),
with_previous_month AS (
    SELECT
        *,
        LAG(month_start) OVER (
            ORDER BY month_start
        ) AS previous_month_start,
        LAG(total_ridership) OVER (
            ORDER BY month_start
        ) AS previous_month_total,
        LAG(is_complete) OVER (
            ORDER BY month_start
        ) AS previous_month_complete
    FROM monthly_status
)
SELECT
    month_start,
    days_reported,
    full_service_days,
    days_in_month,
    total_ridership,
    is_complete,
    CASE
        WHEN is_complete
            AND previous_month_complete
            AND month_start =
                (previous_month_start + INTERVAL '1 month')::date
        THEN ROUND(
            100.0 * (total_ridership - previous_month_total)
            / NULLIF(previous_month_total, 0),
            2
        )
    END AS mom_change_pct
FROM with_previous_month;

-- Display the latest 12 months using month names.
SELECT
    TO_CHAR(month_start, 'FMMonth YYYY') AS month,
    days_reported,
    full_service_days,
    days_in_month,
    total_ridership,
    is_complete,
    mom_change_pct
FROM mart_monthly_ridership
ORDER BY month_start DESC
LIMIT 12;

-- Ten highest daily totals with all five services reported.
SELECT
    'Highest' AS ranking_group,
    date,
    total_ridership,
    service_count
FROM mart_daily_ridership
WHERE service_count = 5
ORDER BY total_ridership DESC, date DESC
LIMIT 10;

-- Ten lowest daily totals with all five services reported.
SELECT
    'Lowest' AS ranking_group,
    date,
    total_ridership,
    service_count
FROM mart_daily_ridership
WHERE service_count = 5
ORDER BY total_ridership ASC, date DESC
LIMIT 10;

-- Calculate service shares using dates with all five services.
CREATE OR REPLACE VIEW mart_service_share AS
WITH service_totals AS (
    SELECT
        r.service,
        MIN(r.date) AS first_date,
        MAX(r.date) AS latest_date,
        COUNT(*) AS days_reported,
        SUM(r.ridership) AS total_ridership
    FROM ktmb_ridership AS r
    JOIN mart_daily_ridership AS d
        ON r.date = d.date
    WHERE d.service_count = 5
    GROUP BY r.service
)
SELECT
    service,
    first_date,
    latest_date,
    days_reported,
    total_ridership,
    ROUND(
        100.0 * total_ridership
        / NULLIF(SUM(total_ridership) OVER (), 0),
        2
    ) AS ridership_share_pct
FROM service_totals;

-- Display services from largest share to smallest.
SELECT
    service,
    first_date,
    latest_date,
    days_reported,
    total_ridership,
    ridership_share_pct
FROM mart_service_share
ORDER BY total_ridership DESC, service;