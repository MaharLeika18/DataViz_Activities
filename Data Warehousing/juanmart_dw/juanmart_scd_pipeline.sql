-- ============================================================
-- juanmart_scd_pipeline.sql
-- SCD Type 2 Implementation: Customer Dimension (region history)
-- ============================================================
-- Purpose: Track changes to a customer's region/address over time,
-- so historical sales can be mapped to where the customer lived
-- AT THE TIME OF PURCHASE, rather than their current address.

DROP TABLE IF EXISTS dim_customer CASCADE;

CREATE TABLE dim_customer (
    customer_sk         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- surrogate key (unique per version)
    customer_id         INT NOT NULL,          -- natural/business key (stable per real customer)
    cust_name            VARCHAR(100) NOT NULL,
    region               VARCHAR(100) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date   DATE,                  -- NULL = still current
    is_current           BOOLEAN NOT NULL DEFAULT TRUE
);

-- ------------------------------------------------------------
-- Seed initial customer records (version 1 for each customer)
-- customer_id assigned manually here since raw data has no ID;
-- in production this would map to a real customer_id from the
-- web form / CRM system.
-- ------------------------------------------------------------
INSERT INTO dim_customer
    (customer_id, cust_name, region, effective_start_date, effective_end_date, is_current)
VALUES
    (1, 'Juan Dela Cruz',  'National Capital Region', '2026-07-01', NULL, TRUE),
    (2, 'Maria Santos',    'National Capital Region', '2026-07-02', NULL, TRUE),
    (3, 'Unknown',         'National Capital Region', '2026-07-02', NULL, TRUE),
    (4, 'Pedro Penduko',   'Region IV-A',              '2026-07-03', NULL, TRUE),
    (5, 'Ana Roces',       'Region IV-A',              '2026-07-04', NULL, TRUE),
    (6, 'Jose Rizal',      'Region IV-A',              '2026-07-05', NULL, TRUE),
    (7, 'Cardo Dalisay',   'National Capital Region', '2026-07-05', NULL, TRUE),
    (8, 'Unknown',         'National Capital Region', '2026-07-06', NULL, TRUE),
    (9, 'Manny Pacquiao',  'Region IV-A',              '2026-07-06', NULL, TRUE),
    (10,'Catriona Gray',   'National Capital Region', '2026-07-07', NULL, TRUE);

-- ============================================================
-- SCD TYPE 2 UPDATE PROCEDURE
-- When a customer's region changes, run these two steps:
--   1) Close out the old record (set end date, flip is_current off)
--   2) Insert a new row with the new region as the current version
-- ============================================================

-- Example: Ana Roces (customer_id 5) moves from Region IV-A
-- to National Capital Region on 2026-07-20.

-- Step 1: Expire the old record
UPDATE dim_customer
SET effective_end_date = '2026-07-19',
    is_current = FALSE
WHERE customer_id = 5
  AND is_current = TRUE;

-- Step 2: Insert the new current record
INSERT INTO dim_customer
    (customer_id, cust_name, region, effective_start_date, effective_end_date, is_current)
VALUES
    (5, 'Ana Roces', 'National Capital Region', '2026-07-20', NULL, TRUE);

-- ============================================================
-- HOW THIS FEEDS THE DASHBOARD (Geographic Heatmap):
-- Instead of joining sales to dim_customer on customer_id alone,
-- join on customer_id AND match order_date to the version of the
-- customer record where order_date falls between
-- effective_start_date and effective_end_date (or effective_end_date
-- IS NULL for the current version). This gives the region the
-- customer lived in AT THE TIME OF EACH PURCHASE, not just today.
-- ============================================================

-- Example query joining a fact table (juanmart_sales) to this
-- dimension using point-in-time logic:
--
-- SELECT
--     f.transaction_id,
--     f.order_date,
--     f.amount_paid,
--     d.region AS region_at_time_of_purchase
-- FROM juanmart_sales f
-- JOIN dim_customer d
--     ON f.customer_id = d.customer_id
--     AND f.order_date >= d.effective_start_date
--     AND (f.order_date <= d.effective_end_date OR d.effective_end_date IS NULL);
--
-- NOTE: juanmart_sales does not currently have a customer_id column
-- (it only has cust_name). This join will not work until customer_id
-- is added to the fact table/schema — flag this with the 1.1/1.2 team.
