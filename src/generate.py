import os
import random
import unicodedata
from datetime import date, datetime, time, timedelta
from time import perf_counter

import psycopg
from dotenv import load_dotenv
from faker import Faker

Faker.seed(23)          # reproducible fake data
random.seed(23)         # reproducible random choices
fake_en = Faker("en_US")
fake_vi = Faker("vi_VN")

load_dotenv()   # reads .env into environment variables

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

CATEGORIES = {
    "Electronics":       ["Mobile Phones", "Laptops", "Headphones", "Cameras"],
    "Fashion":           ["Men's Clothing", "Women's Clothing", "Shoes", "Bags"],
    "Home & Kitchen":    ["Furniture", "Cookware", "Bedding", "Home Decor"],
    "Beauty & Health":   ["Skincare", "Makeup", "Fragrances", "Supplements"],
    "Sports & Outdoors": ["Fitness Equipment", "Camping", "Cycling", "Sportswear"],
}

SHOP_SUFFIXES = ["Store", "Mart", "Shop", "World", "Hub", "Official"]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com"]
PHONE_PREFIXES = ["090", "091", "093", "097", "098", "086", "088"]

MONTH_THEMES = {
    1: ["1.1 Mega Sale", "New Year Sale", "Tết Shopping Festival"],
    2: ["2.2 Mega Sale", "Valentine Deals", "Back to Work Sale"],
    3: ["3.3 Super Sale", "Women's Day Sale", "Spring Sale"],
    4: ["4.4 Mega Sale", "Reunification Day Sale", "Summer Kickoff"],
}
FIXED_DISCOUNTS = [10_000, 20_000, 30_000, 50_000]     # VND, all below the cheapest product (100,000)

PRICE_RANGES = {                      # VND, per main category; min 100,000 keeps fixed discounts safe
    "Electronics":       (500_000, 50_000_000),
    "Fashion":           (100_000, 3_000_000),
    "Home & Kitchen":    (100_000, 20_000_000),
    "Beauty & Health":   (100_000, 2_000_000),
    "Sports & Outdoors": (100_000, 15_000_000),
}

MODEL_WORDS = ["Pro", "Lite", "Max", "Plus", "Mini", "Classic", "Ultra", "Air"]

def country_max(max_len=50):
    """Return a Faker country that fits VARCHAR(max_len)."""
    while True:
        c = fake_en.country()
        if len(c) <= max_len:
            return c

def gen_brands(n=20):
    rows = []
    for _ in range(n):
        rows.append((
            fake_en.unique.company(),
            country_max(),
            fake_en.date_time_between(datetime(2024, 1, 1), datetime(2024, 5, 31)),
        ))
    return rows


def insert_categories(cur):
    """Insert main categories, then their subs. Returns the sub-categories (for product)."""
    sub_categories = []
    for main_name, subs in CATEGORIES.items():
        main_created = fake_en.date_time_between(datetime(2024, 1, 1), datetime(2024, 3, 31))
        cur.execute(
            """INSERT INTO category (category_name, parent_category_id, level, created_at)
               VALUES (%s, NULL, 1, %s)
               RETURNING category_id""",
            (main_name, main_created),
        )
        main_id = cur.fetchone()[0]          # the ID Postgres just assigned

        for sub_name in subs:
            sub_created = fake_en.date_time_between(main_created, datetime(2024, 5, 31))
            cur.execute(
                """INSERT INTO category (category_name, parent_category_id, level, created_at)
                   VALUES (%s, %s, 2, %s)
                   RETURNING category_id""",
                (sub_name, main_id, sub_created),
            )
            sub_categories.append({
                "id": cur.fetchone()[0],
                "name": sub_name,
                "main": main_name,
                "created_at": sub_created,
            })
    return sub_categories

def gen_sellers(n=50):
    rows, used_names = [], set()
    while len(rows) < n:
        name = f"{fake_en.word().capitalize()}{random.choice(SHOP_SUFFIXES)} VN"   # e.g. "TechWorld VN"
        if name in used_names:          # avoid duplicate shop names
            continue
        used_names.add(name)
        rows.append((
            name,
            fake_en.date_between(date(2024, 1, 1), date(2024, 12, 31)),            # DATE, no time
            random.choices(["Official", "Marketplace"], weights=[20, 80], k=1)[0],  # ~20% official
            round(random.uniform(3, 5), 1),                                         # 3.0–5.0
        ))
    return rows

def to_ascii(text):
    """'Nguyễn Văn Đức' -> 'Nguyen Van Duc'"""
    text = text.replace("đ", "d").replace("Đ", "D")       # đ doesn't decompose, handle it first
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def gen_customers(n=30_000):
    rows, used_phones = [], set()
    for i in range(1, n + 1):
        gender = random.choice(["Male", "Female"])
        name = fake_vi.name_male() if gender == "Male" else fake_vi.name_female()

        local_part = to_ascii(name).lower().replace(" ", "")
        email = f"{local_part}{i}@{random.choice(EMAIL_DOMAINS)}"      # i → always unique

        while True:                                                   # unique 10-digit mobile
            phone = random.choice(PHONE_PREFIXES) + f"{random.randint(0, 9_999_999):07d}"
            if phone not in used_phones:
                used_phones.add(phone)
                break

        rows.append((
            name,
            email,
            phone,
            gender,
            fake_vi.street_address(),          # street only, no city inside
            fake_vi.city(),
            fake_vi.date_time_between(datetime(2024, 1, 1), datetime(2024, 12, 31)),
        ))
    return rows

def gen_promotions(n=30):
    rows = []
    for _ in range(n):
        start = fake_en.date_between(date(2025, 1, 1), date(2025, 4, 30))
        end = start + timedelta(days=random.randint(30, 50))

        # created_at: Dec 2024 – Jan 2025, but never after the start date
        latest = min(datetime(2025, 1, 31, 23, 59, 59), datetime.combine(start, time.min))
        created = fake_en.date_time_between(datetime(2024, 12, 1), latest)

        discount_type = random.choice(["percentage", "fixed_amount"])
        if discount_type == "percentage":
            discount_value = random.choice(range(5, 55, 5))          # 5, 10, ..., 50 (%)
        else:
            discount_value = random.choice(FIXED_DISCOUNTS)

        rows.append((
            random.choice(MONTH_THEMES[start.month]),
            random.choices(["product", "category", "seller", "flash_sale"],
                           weights=[40, 25, 20, 15], k=1)[0],
            discount_type,
            discount_value,
            start,
            end,
            created,
        ))
    return rows

def gen_products(brand_rows, sub_categories, seller_rows, n=3_000):
    rows = []
    for _ in range(n):
        brand = random.choice(brand_rows)
        category = random.choice(sub_categories)        # level-2 only
        seller = random.choice(seller_rows)

        # product can't exist before its brand, category or seller
        start = max(
            datetime(2024, 6, 1),
            brand["created_at"],
            category["created_at"],
            datetime.combine(seller["join_date"], time.min),   # DATE -> datetime to compare
        )
        created = fake_en.date_time_between(start, datetime(2024, 12, 31, 23, 59, 59))

        low, high = PRICE_RANGES[category["main"]]
        price = round(random.uniform(low, high), -3)           # round to thousands VND

        name = f"{brand['name']} {category['name']} {random.choice(MODEL_WORDS)} {random.randint(1, 99)}"

        rows.append((
            name,
            category["id"],
            brand["id"],
            seller["id"],
            price,
            random.randint(0, 500),
            round(random.uniform(3, 5), 1),
            created,
            random.random() < 0.9,                              # ~90% active
        ))
    return rows

def gen_promotion_products(promo_rows, product_rows, total=500):
    active = [p for p in product_rows if p["is_active"]]

    # split 500 links over 30 promos: 500 // 30 = 16, remainder 20 → 20 promos get 17
    n = len(promo_rows)
    counts = [total // n] * n
    for i in range(total % n):
        counts[i] += 1
    random.shuffle(counts)

    rows = []
    for promo, k in zip(promo_rows, counts):
        # which products can this promotion apply to?
        if promo["type"] == "category":
            cat_id = random.choice(active)["category_id"]
            eligible = [p for p in active if p["category_id"] == cat_id]
        elif promo["type"] == "seller":
            seller_id = random.choice(active)["seller_id"]
            eligible = [p for p in active if p["seller_id"] == seller_id]
        else:                                    # "product" or "flash_sale"
            eligible = active

        chosen = random.sample(eligible, min(k, len(eligible)))   # no repeats → UNIQUE can't fail

        # link set up after the promo was created, before it starts
        link_latest = datetime.combine(promo["start_date"], time.min)
        for p in chosen:
            created = fake_en.date_time_between(promo["created_at"], link_latest)
            rows.append((promo["id"], p["id"], created))
    return rows



def main():
    brands = gen_brands()

    with psycopg.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""TRUNCATE brand, category, seller, customer, promotion, product, promotion_product
               RESTART IDENTITY CASCADE""")

            cur.executemany(
                "INSERT INTO brand (brand_name, country, created_at) VALUES (%s, %s, %s)",
                brands,
            )

            cur.execute("SELECT brand_id, brand_name, created_at FROM brand")
            brand_rows = [{"id": r[0], "name": r[1], "created_at": r[2]} for r in cur.fetchall()]
            print(f"Inserted {len(brand_rows)} brands")

            sub_categories = insert_categories(cur)
            print(f"Inserted {len(CATEGORIES)} main + {len(sub_categories)} sub categories")

            sellers = gen_sellers()
            cur.executemany(
                "INSERT INTO seller (seller_name, join_date, seller_type, rating) VALUES (%s, %s, %s, %s)",
                sellers,
            )
            cur.execute("SELECT seller_id, join_date FROM seller")
            seller_rows = [{"id": r[0], "join_date": r[1]} for r in cur.fetchall()]
            print(f"Inserted {len(seller_rows)} sellers")

            t0 = perf_counter()
            customers = gen_customers()
            print(customers[:2])
            cur.executemany(
                """INSERT INTO customer
                   (customer_name, email, phone, gender, address, city, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                customers,
            )
            print(f"Inserted {len(customers)} customers in {perf_counter() - t0:.1f}s")


            promotions = gen_promotions()
            cur.executemany(
                """INSERT INTO promotion
                   (promotion_name, promotion_type, discount_type, discount_value,
                    start_date, end_date, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                promotions,
            )
            cur.execute("SELECT promotion_id, promotion_type, start_date, created_at FROM promotion")
            promo_rows = [
                {"id": r[0], "type": r[1], "start_date": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]
            print(f"Inserted {len(promo_rows)} promotions")

            products = gen_products(brand_rows, sub_categories, seller_rows)
            print(products[:2])
            cur.executemany(
                """INSERT INTO product
                   (product_name, category_id, brand_id, seller_id, price,
                    stock_qty, rating, created_at, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                products,
            )

            cur.execute("SELECT product_id, category_id, seller_id, created_at, is_active FROM product")
            product_rows = [
                {"id": r[0], "category_id": r[1], "seller_id": r[2],
                 "created_at": r[3], "is_active": r[4]}
                for r in cur.fetchall()
            ]
            print(f"Inserted {len(product_rows)} products")

            promo_products = gen_promotion_products(promo_rows, product_rows)
            cur.executemany(
                "INSERT INTO promotion_product (promotion_id, product_id, created_at) VALUES (%s, %s, %s)",
                promo_products,
            )
            print(f"Inserted {len(promo_products)} promotion-product links")


if __name__ == "__main__":
    main()