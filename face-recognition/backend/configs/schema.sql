-- configs/schema.sql
-- Run with: docker exec -i safeguardai-postgres psql -U safeguard -d safeguardai < configs/schema.sql

CREATE TABLE IF NOT EXISTS people (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    employee_id     VARCHAR(100) UNIQUE,
    role            VARCHAR(255),
    department      VARCHAR(255),
    notes           TEXT,
    photo_path      VARCHAR(500),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mirrors what's stored in FAISS -- kept here too for audit/rebuild purposes.
-- FAISS is the source of truth for FAST search; this table lets us rebuild
-- the FAISS index from scratch if it's ever lost/corrupted, and lets a person
-- have MORE THAN ONE enrolled photo/embedding (better accuracy across angles/lighting).
CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    person_id       INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    faiss_index_id  INTEGER NOT NULL UNIQUE,  -- the row's position in the FAISS index
    embedding       FLOAT8[] NOT NULL,        -- the 512-d normed_embedding, stored as an array
    source_photo    VARCHAR(500),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recognition_logs (
    id                  SERIAL PRIMARY KEY,
    person_id           INTEGER REFERENCES people(id) ON DELETE SET NULL,  -- NULL if unknown
    source              VARCHAR(255) NOT NULL,   -- e.g. "Cam-01 - Lobby" or uploaded filename
    timestamp_in_video  FLOAT,                   -- seconds into the video, NULL for images/live
    confidence          FLOAT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'unknown',  -- 'known' | 'unknown' | 'spoof'
    thumbnail_path      VARCHAR(500),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    filename        VARCHAR(500) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued | processing | done | failed
    progress        FLOAT NOT NULL DEFAULT 0.0,
    error_message   TEXT,
    result_path     VARCHAR(500),  -- annotated output video/image path once done
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recognition_logs_person_id ON recognition_logs(person_id);
CREATE INDEX IF NOT EXISTS idx_recognition_logs_created_at ON recognition_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_embeddings_person_id ON embeddings(person_id);