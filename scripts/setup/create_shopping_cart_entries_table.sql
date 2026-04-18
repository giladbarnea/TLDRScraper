CREATE TABLE IF NOT EXISTS shopping_cart_entries (
    id UUID PRIMARY KEY,
    person_name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_in_dollars NUMERIC NOT NULL DEFAULT 0,
    input_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE shopping_cart_entries
    ADD COLUMN IF NOT EXISTS price_in_dollars NUMERIC NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS shopping_cart_entries_created_at_idx
    ON shopping_cart_entries (created_at DESC);
