CREATE TABLE IF NOT EXISTS research_records (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    intent TEXT NOT NULL,
    velocity REAL NOT NULL,
    competition REAL NOT NULL,
    source TEXT NOT NULL,
    freshness_ts TEXT NOT NULL,
    confidence REAL NOT NULL,
    raw TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_research_velocity ON research_records (velocity DESC);
CREATE INDEX IF NOT EXISTS idx_research_confidence ON research_records (confidence DESC);
CREATE INDEX IF NOT EXISTS idx_research_freshness_ts ON research_records (freshness_ts DESC);
