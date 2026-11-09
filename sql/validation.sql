-- ============================================================
-- Project 03 - Data validation
-- Each check counts rows that BREAK a rule: 0 = PASS
-- ============================================================

\echo '=== 1. Row counts ==='
SELECT tbl, actual, expected,
       CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
              SELECT 'brand'             AS tbl, (SELECT COUNT(*) FROM brand)             AS actual, 20    AS expected
    UNION ALL SELECT 'category',                 (SELECT COUNT(*) FROM category),                    25
    UNION ALL SELECT 'seller',                   (SELECT COUNT(*) FROM seller),                      50
    UNION ALL SELECT 'customer',                 (SELECT COUNT(*) FROM customer),                    30000
    UNION ALL SELECT 'product',                  (SELECT COUNT(*) FROM product),                     3000
    UNION ALL SELECT 'promotion',                (SELECT COUNT(*) FROM promotion),                   30
    UNION ALL SELECT 'promotion_product',        (SELECT COUNT(*) FROM promotion_product),           500
) t;

\echo '=== 2. Business rules the database does NOT enforce ==='
SELECT check_name, violations,
       CASE WHEN violations = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'category: sub-category parent is not level 1' AS check_name,
           (SELECT COUNT(*) FROM category c JOIN category p ON c.parent_category_id = p.category_id
            WHERE p.level <> 1) AS violations

    UNION ALL SELECT 'category: child created before parent',
           (SELECT COUNT(*) FROM category c JOIN category p ON c.parent_category_id = p.category_id
            WHERE c.created_at < p.created_at)

    UNION ALL SELECT 'product: linked to a main (level 1) category',
           (SELECT COUNT(*) FROM product p JOIN category c USING (category_id) WHERE c.level = 1)

    UNION ALL SELECT 'product: created before its category',
           (SELECT COUNT(*) FROM product p JOIN category c USING (category_id)
            WHERE p.created_at < c.created_at)

    UNION ALL SELECT 'product: created before its brand',
           (SELECT COUNT(*) FROM product p JOIN brand b USING (brand_id)
            WHERE p.created_at < b.created_at)

    UNION ALL SELECT 'product: created before seller joined',
           (SELECT COUNT(*) FROM product p JOIN seller s USING (seller_id)
            WHERE p.created_at::date < s.join_date)

    UNION ALL SELECT 'promo_product: link created before promotion',
           (SELECT COUNT(*) FROM promotion_product pp JOIN promotion pr USING (promotion_id)
            WHERE pp.created_at < pr.created_at)

    UNION ALL SELECT 'promo_product: link created after promotion start',
           (SELECT COUNT(*) FROM promotion_product pp JOIN promotion pr USING (promotion_id)
            WHERE pp.created_at::date > pr.start_date)

    UNION ALL SELECT 'promo_product: inactive product in a promotion',
           (SELECT COUNT(*) FROM promotion_product pp JOIN product p USING (product_id)
            WHERE NOT p.is_active)

    UNION ALL SELECT 'promo_product: fixed discount >= product price',
           (SELECT COUNT(*) FROM promotion_product pp
            JOIN promotion pr USING (promotion_id) JOIN product p USING (product_id)
            WHERE pr.discount_type = 'fixed_amount' AND pr.discount_value >= p.price)

    UNION ALL SELECT 'promotion: category promo spans >1 category',
           (SELECT COUNT(*) FROM (
                SELECT pp.promotion_id
                FROM promotion_product pp
                JOIN promotion pr USING (promotion_id) JOIN product p USING (product_id)
                WHERE pr.promotion_type = 'category'
                GROUP BY pp.promotion_id
                HAVING COUNT(DISTINCT p.category_id) > 1) x)

    UNION ALL SELECT 'promotion: seller promo spans >1 seller',
           (SELECT COUNT(*) FROM (
                SELECT pp.promotion_id
                FROM promotion_product pp
                JOIN promotion pr USING (promotion_id) JOIN product p USING (product_id)
                WHERE pr.promotion_type = 'seller'
                GROUP BY pp.promotion_id
                HAVING COUNT(DISTINCT p.seller_id) > 1) x)
) checks;

\echo '=== 3. Data profile (look, no PASS/FAIL) ==='
SELECT seller_type, COUNT(*) FROM seller GROUP BY seller_type;
SELECT gender, COUNT(*) FROM customer GROUP BY gender;
SELECT is_active, COUNT(*) FROM product GROUP BY is_active;

SELECT pc.category_name AS main_category,
       COUNT(*) AS products, MIN(p.price) AS min_price, MAX(p.price) AS max_price
FROM product p
JOIN category c  ON c.category_id  = p.category_id
JOIN category pc ON pc.category_id = c.parent_category_id
GROUP BY pc.category_name
ORDER BY pc.category_name;

SELECT EXTRACT(MONTH FROM start_date) AS start_month, COUNT(*) AS promotions
FROM promotion GROUP BY 1 ORDER BY 1;

\echo '=== 4. Samples ==='
SELECT customer_name, email, phone, gender, city FROM customer LIMIT 5;
SELECT product_name, price, stock_qty, is_active FROM product LIMIT 5;
