-- Supabase SQL Schema for Crypto Pivot Analysis
-- Run this in your Supabase SQL Editor

-- Table 1: Historical 15-minute candle data
CREATE TABLE IF NOT EXISTS candles_15m (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(30, 8) NOT NULL,
    turnover NUMERIC(30, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure no duplicate candles
    UNIQUE(ticker, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_candles_ticker_time ON candles_15m(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON candles_15m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_candles_ticker ON candles_15m(ticker);

-- Table 2: Pre-computed pivot analysis cache
CREATE TABLE IF NOT EXISTS pivot_analysis_cache (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL, -- 'daily', 'weekly', etc.
    date_range_days INTEGER NOT NULL,
    weekdays INTEGER[] NOT NULL,
    pivot_table JSONB NOT NULL,
    stats JSONB NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint for cache key
    UNIQUE(ticker, timeframe, date_range_days, weekdays)
);

-- Indexes for pivot cache
CREATE INDEX IF NOT EXISTS idx_pivot_ticker ON pivot_analysis_cache(ticker, last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_pivot_timeframe ON pivot_analysis_cache(ticker, timeframe);

-- Table 3: Popular pairs configuration
CREATE TABLE IF NOT EXISTS popular_pairs (
    ticker VARCHAR(20) PRIMARY KEY,
    priority INTEGER DEFAULT 1,
    auto_update BOOLEAN DEFAULT true,
    update_interval_minutes INTEGER DEFAULT 15,
    last_fetched TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert popular pairs (modify as needed)
INSERT INTO popular_pairs (ticker, priority, auto_update) VALUES
    ('BTCUSDT', 1, true),
    ('ETHUSDT', 2, true),
    ('SOLUSDT', 3, true),
    ('BNBUSDT', 4, true),
    ('XRPUSDT', 5, true),
    ('ADAUSDT', 6, true),
    ('DOGEUSDT', 7, true),
    ('MATICUSDT', 8, true),
    ('LINKUSDT', 9, true),
    ('AVAXUSDT', 10, true),
    ('DOTUSDT', 11, true),
    ('UNIUSDT', 12, true),
    ('LTCUSDT', 13, true),
    ('NEARUSDT', 14, true),
    ('ATOMUSDT', 15, true)
ON CONFLICT (ticker) DO NOTHING;

-- Table 4: Update logs (for monitoring)
CREATE TABLE IF NOT EXISTS update_logs (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    update_type VARCHAR(50) NOT NULL, -- 'candles', 'pivot_cache'
    rows_affected INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_ticker_time ON update_logs(ticker, created_at DESC);

-- Enable Row Level Security (RLS) for public access
ALTER TABLE candles_15m ENABLE ROW LEVEL SECURITY;
ALTER TABLE pivot_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE popular_pairs ENABLE ROW LEVEL SECURITY;

-- Create policies for read access (public)
CREATE POLICY "Allow public read access on candles_15m"
    ON candles_15m FOR SELECT
    USING (true);

CREATE POLICY "Allow public read access on pivot_analysis_cache"
    ON pivot_analysis_cache FOR SELECT
    USING (true);

CREATE POLICY "Allow public read access on popular_pairs"
    ON popular_pairs FOR SELECT
    USING (true);

-- Function to get latest candle timestamp for a ticker
CREATE OR REPLACE FUNCTION get_latest_candle_timestamp(p_ticker VARCHAR)
RETURNS TIMESTAMPTZ AS $$
BEGIN
    RETURN (
        SELECT timestamp
        FROM candles_15m
        WHERE ticker = p_ticker
        ORDER BY timestamp DESC
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function to clean old cache entries (keep last 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM pivot_analysis_cache
    WHERE last_updated < NOW() - INTERVAL '7 days';
    
    DELETE FROM update_logs
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE candles_15m IS 'Historical 15-minute OHLCV candle data for crypto pairs';
COMMENT ON TABLE pivot_analysis_cache IS 'Pre-computed pivot analysis results for fast loading';
COMMENT ON TABLE popular_pairs IS 'Configuration for which pairs to auto-update';
COMMENT ON TABLE update_logs IS 'Monitoring logs for data updates';

