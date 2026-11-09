# E-commerce Synthetic Data (Project 03 – Python in Data)

Generates synthetic data for an e-commerce OLTP system with Python + Faker
and loads it into PostgreSQL, keeping all foreign keys and business rules consistent.

## Schema

(paste the Mermaid ERD here)

## Data volume

| Table             | Rows                 |
| ----------------- | -------------------- |
| brand             | 20                   |
| category          | 25 (5 main + 20 sub) |
| seller            | 50                   |
| customer          | 30,000               |
| product           | 3,000                |
| promotion         | 30                   |
| promotion_product | 500                  |

`order` and `order_item` are created empty; they are filled in Project 04.

## How to run

1. `uv sync`
2. Copy `.env.example` to `.env` and set your database password
3. `psql -h localhost -U postgres -c "CREATE DATABASE ecommerce;"`
4. `psql -h localhost -U postgres -d ecommerce -f sql/schema.sql`
5. `uv run src/generate.py`
6. `psql -h localhost -U postgres -d ecommerce -f sql/validation.sql`

## Data quality rules

Enforced by the database: PK, FK, UNIQUE, CHECK constraints.
Enforced by the generator:

- Products only in level-2 categories; created after their brand, category and seller
- Customer name matches gender; email built from name; unique Vietnamese mobile numbers
- Promotion created before it starts; link created between promo creation and start
- Category/seller promotions only include products of one category/seller
- Fixed discounts (max 50,000 VND) below the cheapest product (100,000 VND)
  Results: `docs/validation_results.txt`

## Notes on the brief

- Faker date hints with string dates ('2024-01-01') are replaced by `datetime` objects
- Faker `country()` can exceed VARCHAR(50) → regenerated, not truncated
- Promotion start dates end April 30, so ~7–8 promos/month Jan–Apr (brief says ~6/month Jan–May)
- ~167 orders/customer is unrealistic but needed for Project 04 volume
