-- ============================================================
-- Table: landing.pipeline_metadata
-- Purpose: Track Airflow ingestion and transformation runs.
-- Grain: One row per pipeline execution.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.pipeline_metadata (
    id             BIGSERIAL PRIMARY KEY,
    pipeline_name  VARCHAR(100) NOT NULL,
    ticker         VARCHAR(20),
    status         VARCHAR(50) NOT NULL,
    rows_processed INTEGER,
    error_message  TEXT,

    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Supports filtering pipeline runs by execution status.
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_status
    ON landing.pipeline_metadata (status);

-- Supports retrieving the latest pipeline execution records.
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_created_at
    ON landing.pipeline_metadata (created_at DESC);

-- Supports retrieving execution history for a specific
-- pipeline and ticker, with the most recent runs first.
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_pipeline_ticker_started
    ON landing.pipeline_metadata
    (pipeline_name, ticker, started_at DESC);