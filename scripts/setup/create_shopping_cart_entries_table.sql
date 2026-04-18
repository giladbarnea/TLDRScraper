CREATE TABLE IF NOT EXISTS shopping_cart_entries (
    id UUID PRIMARY KEY,
    person_name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    input_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS shopping_cart_entries_created_at_idx
    ON shopping_cart_entries (created_at DESC);
