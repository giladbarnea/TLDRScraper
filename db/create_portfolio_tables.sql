CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id UUID PRIMARY KEY,
    symbol_id TEXT NOT NULL,
    transaction_amount_dollars NUMERIC NOT NULL,
    shares NUMERIC NOT NULL,
    entry_kind TEXT NOT NULL DEFAULT 'trade',
    transaction_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE portfolio_transactions
    ADD COLUMN IF NOT EXISTS entry_kind TEXT NOT NULL DEFAULT 'trade';

ALTER TABLE portfolio_transactions
    ALTER COLUMN entry_kind SET DEFAULT 'trade';

ALTER TABLE portfolio_transactions
    ALTER COLUMN entry_kind SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'portfolio_transactions_entry_kind_check'
    ) THEN
        ALTER TABLE portfolio_transactions
            ADD CONSTRAINT portfolio_transactions_entry_kind_check
            CHECK (entry_kind IN ('snapshot', 'trade'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS portfolio_transactions_transaction_timestamp_idx
    ON portfolio_transactions (transaction_timestamp DESC);

CREATE INDEX IF NOT EXISTS portfolio_transactions_symbol_timestamp_idx
    ON portfolio_transactions (symbol_id, transaction_timestamp DESC);

CREATE TABLE IF NOT EXISTS portfolio_latest_close_rates (
    symbol_id TEXT PRIMARY KEY,
    close_price NUMERIC NOT NULL CHECK (close_price > 0),
    close_date DATE NOT NULL,
    source_symbol TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_historical_close_rates (
    symbol_id TEXT NOT NULL,
    requested_date DATE NOT NULL,
    close_price NUMERIC NOT NULL CHECK (close_price > 0),
    close_date DATE NOT NULL,
    source_symbol TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol_id, requested_date)
);
