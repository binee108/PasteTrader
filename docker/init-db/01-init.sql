-- PasteTrader Database Initialization Script
-- This script runs automatically when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create application schema
CREATE SCHEMA IF NOT EXISTS app;

-- Grant permissions
GRANT ALL ON SCHEMA app TO pastetrader;
GRANT ALL ON ALL TABLES IN SCHEMA app TO pastetrader;
GRANT ALL ON ALL SEQUENCES IN SCHEMA app TO pastetrader;

-- Set default search path
ALTER DATABASE pastetrader SET search_path TO app, public;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'PasteTrader database initialized successfully';
END $$;
