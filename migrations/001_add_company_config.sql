-- Migration: Add company_config table and update sync_history
-- Date: 2026-01-10
-- Description: Add multi-company support with period tracking

-- Create company_config table if not exists
CREATE TABLE IF NOT EXISTS company_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    company_guid TEXT DEFAULT '',
    company_alterid INTEGER DEFAULT 0,
    last_alter_id_master INTEGER DEFAULT 0,
    last_alter_id_transaction INTEGER DEFAULT 0,
    books_from TEXT DEFAULT '',
    books_to TEXT DEFAULT '',
    last_sync_at TEXT,
    last_sync_type TEXT,
    sync_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for company_config
CREATE INDEX IF NOT EXISTS idx_company_config_name ON company_config(company_name);
CREATE INDEX IF NOT EXISTS idx_company_config_guid ON company_config(company_guid);

-- Add books_from column to company_config if not exists
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a try-catch approach in Python

-- Add books_to column to company_config if not exists

-- Add company_name column to sync_history if not exists

-- Note: The actual column additions are handled in database_service.py
-- because SQLite doesn't support conditional ALTER TABLE statements
