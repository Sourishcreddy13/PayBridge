-- Migration 001 is append-only. Future migrations add new tables/columns and never rewrite business rows.
CREATE TABLE IF NOT EXISTS migration_marker (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
INSERT INTO migration_marker(version, applied_at) VALUES ('001_initial', CURRENT_TIMESTAMP);
