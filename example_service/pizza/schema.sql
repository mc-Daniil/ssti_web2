-- Compatible with the original tables: existing records and integer IDs are retained.
CREATE TABLE IF NOT EXISTS "user" (
 id SERIAL PRIMARY KEY, email VARCHAR(254) UNIQUE NOT NULL,
 name VARCHAR(100) NOT NULL, password_hash VARCHAR(255) NOT NULL,
 is_staff BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS token (
 id SERIAL PRIMARY KEY, digest VARCHAR(64) UNIQUE NOT NULL,
 user_id INTEGER NOT NULL REFERENCES "user"(id), expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS pizza (
 id SERIAL PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL,
 price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);
CREATE TABLE IF NOT EXISTS delivery (
 id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES "user"(id),
 address VARCHAR(1024) NOT NULL, phone VARCHAR(40) NOT NULL,
 status VARCHAR(30) NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_delivery_user_id ON delivery(user_id);
CREATE TABLE IF NOT EXISTS delivery_item (
 id SERIAL PRIMARY KEY, delivery_id INTEGER NOT NULL REFERENCES delivery(id),
 pizza_id INTEGER NOT NULL REFERENCES pizza(id), name VARCHAR(100) NOT NULL,
 quantity INTEGER NOT NULL CHECK (quantity > 0), price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);
CREATE INDEX IF NOT EXISTS ix_delivery_item_delivery_id ON delivery_item(delivery_id);
