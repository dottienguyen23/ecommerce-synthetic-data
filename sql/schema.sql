-- Re-runnable: drop everything first. CASCADE also drops dependent FKs.
DROP TABLE IF EXISTS order_item, "order", promotion_product, promotion,
                     product, customer, seller, category, brand CASCADE;

CREATE TABLE brand (
    brand_id    SERIAL PRIMARY KEY,
    brand_name  VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(50),
    created_at  TIMESTAMP
);

CREATE TABLE category (
    category_id        SERIAL PRIMARY KEY,
    category_name      VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT REFERENCES category(category_id),
    level              SMALLINT NOT NULL CHECK (level IN (1, 2)),
    created_at         TIMESTAMP,
    CHECK ((level = 1 AND parent_category_id IS NULL)
        OR (level = 2 AND parent_category_id IS NOT NULL))
);

CREATE TABLE seller (
    seller_id    SERIAL PRIMARY KEY,
    seller_name  VARCHAR(150) NOT NULL,
    join_date    DATE,
    seller_type  VARCHAR(50) CHECK (seller_type IN ('Official', 'Marketplace')),
    rating       DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    country      VARCHAR(50) DEFAULT 'Vietnam'
);

CREATE TABLE customer (
    customer_id    SERIAL PRIMARY KEY,
    customer_name  VARCHAR(150) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    phone          VARCHAR(20) UNIQUE,
    gender         VARCHAR(10) CHECK (gender IN ('Male', 'Female')),
    address        VARCHAR(255),
    city           VARCHAR(100),
    created_at     TIMESTAMP
);

CREATE TABLE product (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(200) NOT NULL,
    category_id   INT NOT NULL REFERENCES category(category_id),
    brand_id      INT NOT NULL REFERENCES brand(brand_id),
    seller_id     INT NOT NULL REFERENCES seller(seller_id),
    price         DECIMAL(12,2) CHECK (price > 0),
    stock_qty     INT CHECK (stock_qty >= 0),
    rating        DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    created_at    TIMESTAMP,
    is_active     BOOLEAN DEFAULT TRUE
);

CREATE TABLE promotion (
    promotion_id    SERIAL PRIMARY KEY,
    promotion_name  VARCHAR(100) NOT NULL,
    promotion_type  VARCHAR(50) CHECK (promotion_type IN ('product','category','seller','flash_sale')),
    discount_type   VARCHAR(20) CHECK (discount_type IN ('percentage', 'fixed_amount')),
    discount_value  NUMERIC(10,2),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMP,
    CHECK (discount_value > 0 AND (discount_type = 'fixed_amount' OR discount_value <= 100)),
    CHECK (start_date >= created_at::date),
    CHECK (end_date >= start_date)
);

CREATE TABLE promotion_product (
    promo_product_id  SERIAL PRIMARY KEY,
    promotion_id      INT NOT NULL REFERENCES promotion(promotion_id),
    product_id        INT NOT NULL REFERENCES product(product_id),
    created_at        TIMESTAMP,
    UNIQUE (promotion_id, product_id)
);

-- Created now, filled in Project 04
CREATE TABLE "order" (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customer(customer_id),
    order_date    TIMESTAMP NOT NULL,
    status        VARCHAR(20) CHECK (status IN ('PLACED','PAID','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    total_amount  DECIMAL(12,2) DEFAULT 0 CHECK (total_amount >= 0),
    created_at    TIMESTAMP,
    CHECK (created_at >= order_date)
);

CREATE TABLE order_item (
    order_item_id  BIGSERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES "order"(order_id),
    product_id     INT NOT NULL REFERENCES product(product_id),
    order_date     TIMESTAMP NOT NULL,
    quantity       INT CHECK (quantity > 0),
    unit_price     DECIMAL(12,2) CHECK (unit_price > 0),
    subtotal       DECIMAL(12,2),
    created_at     TIMESTAMP,
    CHECK (subtotal = quantity * unit_price),
    CHECK (created_at >= order_date)
);