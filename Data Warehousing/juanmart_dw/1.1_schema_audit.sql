DROP TABLE IF EXISTS juanmart_sales CASCADE;

CREATE TABLE juanmart_sales (
    transaction_id INT PRIMARY KEY NOT NULL,
    cust_name VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    order_date DATE NOT NULL,
    amount_paid FLOAT(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL
);

INSERT INTO juanmart_sales
    (transaction_id, cust_name, region, order_date, amount_paid, status)
VALUES
    (1001, 'Juan Dela Cruz',  'National Capital Region', '2026-07-01', 1500.50, 'Completed'),
    (1002, 'Maria Santos',    'National Capital Region', '2026-07-02', 2400.00, 'Completed'),
    (1003, 'Unknown',         'National Capital Region', '2026-07-02', 450.00,  'Cancelled'),
    (1004, 'Pedro Penduko',   'Region IV-A',              '2026-07-03', 1675.25, 'Completed'),
    (1005, 'Ana Roces',       'Region IV-A',              '2026-07-04', 3100.25, 'Completed'),
    (1006, 'Jose Rizal',      'Region IV-A',              '2026-07-05', 1200.00, 'Returned'),
    (1007, 'Cardo Dalisay',   'National Capital Region', '2026-07-05', 1675.25, 'Completed'),
    (1008, 'Unknown',         'National Capital Region', '2026-07-06', 850.75,  'Completed'),
    (1009, 'Manny Pacquiao',  'Region IV-A',              '2026-07-06', 5000.00, 'Completed'),
    (1010, 'Catriona Gray',   'National Capital Region', '2026-07-07', 1850.00, 'Cancelled');
