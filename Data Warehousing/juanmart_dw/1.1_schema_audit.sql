DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_customer CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_region CASCADE;
DROP TABLE IF EXISTS dim_status CASCADE;

CREATE TABLE dim_customer (
    cust_id INT AUTO_INCREMENT PRIMARY KEY,
    cust_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dim_region (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,         
    full_date DATE NOT NULL UNIQUE,
    day INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    day_of_week VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE dim_status (
    status_id INT AUTO_INCREMENT PRIMARY KEY,
    status_name VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE fact_sales (
    transaction_id INT PRIMARY KEY,
    cust_id INT NOT NULL,
    region_id INT NOT NULL,
    date_id INT NOT NULL,
    status_id INT NOT NULL,
    amount_paid FLOAT(10,2) NOT NULL,

    CONSTRAINT fk_fact_customer FOREIGN KEY (cust_id) REFERENCES dim_customer(cust_id),
    CONSTRAINT fk_fact_region   FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
    CONSTRAINT fk_fact_date     FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    CONSTRAINT fk_fact_status   FOREIGN KEY (status_id) REFERENCES dim_status(status_id)
);