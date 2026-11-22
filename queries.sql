-- Query 1 — JOIN: booking details with customer and vehicle
SELECT bk.booking_id,
       c.first_name || ' ' || c.last_name AS customer_name,
       v.brand || ' ' || v.model AS vehicle,
       bk.pickup_date, bk.return_date, bk.booking_status, bk.total_amount
FROM bookings bk
JOIN customers c ON c.customer_id = bk.customer_id
JOIN vehicles v ON v.vehicle_id = bk.vehicle_id
ORDER BY bk.booking_id;
-- Expected sample rows: (1, Aylin Demir, Toyota Corolla, 2026-12-01, 2026-12-04, CONFIRMED, 5400.00); (2, Mert Kaya, Hyundai Tucson, 2026-12-05, 2026-12-07, PENDING, 5200.00); (3, Deniz Yilmaz, Volkswagen Golf, 2026-11-10, 2026-11-13, COMPLETED, 6300.00).

-- Query 2 — GROUP BY and ORDER BY: booking count and revenue by vehicle
SELECT v.brand || ' ' || v.model AS vehicle,
       COUNT(bk.booking_id) AS booking_count,
       COALESCE(SUM(bk.total_amount), 0) AS total_revenue
FROM vehicles v
LEFT JOIN bookings bk ON bk.vehicle_id = v.vehicle_id
GROUP BY v.vehicle_id, v.brand, v.model
ORDER BY total_revenue DESC, booking_count DESC;
-- Expected leading rows: Volkswagen Golf — 1 booking — 6300.00 TRY; Toyota Corolla — 1 — 5400.00 TRY; Hyundai Tucson — 1 — 5200.00 TRY. Vehicles without bookings remain visible with zero totals.

-- Query 3 — SUBQUERY: vehicles priced above the average daily rate
SELECT vehicle_id, brand, model, daily_rate
FROM vehicles
WHERE daily_rate > (SELECT AVG(daily_rate) FROM vehicles)
ORDER BY daily_rate DESC;
-- With the six seeded vehicles, the average daily rate is 1,916.67 TRY. Expected rows include Hyundai Tucson (2,600), Peugeot 2008 (2,450), Volkswagen Golf (2,100), and any other vehicle whose rate is above the calculated average.
