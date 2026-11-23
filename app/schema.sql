-- Certification Progress Tracker - relational schema (SQLite)
-- 4 tables, 3NF. Foreign keys are enforced with PRAGMA foreign_keys = ON (set in db.py).

DROP TABLE IF EXISTS progress_logs;
DROP TABLE IF EXISTS certifications;
DROP TABLE IF EXISTS providers;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'student'
                          CHECK (role IN ('student', 'mentor')),
    department    TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Providers are a separate table so "AWS" is stored once, not typed
-- differently ("aws", "Amazon", "AWS ") on every certification row.
CREATE TABLE providers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE certifications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_id    INTEGER NOT NULL REFERENCES providers(id),
    title          TEXT    NOT NULL,
    category       TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'planned'
                           CHECK (status IN ('planned', 'in_progress', 'completed', 'dropped')),
    progress       INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    start_date     TEXT,
    target_date    TEXT,
    completed_date TEXT,
    expiry_date    TEXT,
    credential_id  TEXT,
    credential_url TEXT,
    notes          TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    -- a user cannot track the same certification from the same provider twice
    UNIQUE (user_id, provider_id, title)
);

CREATE TABLE progress_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    certification_id INTEGER NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    log_date         TEXT    NOT NULL,
    hours            REAL    NOT NULL CHECK (hours > 0 AND hours <= 24),
    progress         INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
    note             TEXT
);

-- Indexes on the columns we filter / join on most often.
CREATE INDEX idx_cert_user     ON certifications(user_id);
CREATE INDEX idx_cert_status   ON certifications(status);
CREATE INDEX idx_cert_target   ON certifications(target_date);
CREATE INDEX idx_log_cert      ON progress_logs(certification_id);
