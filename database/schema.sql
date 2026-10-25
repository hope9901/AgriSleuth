-- Idempotent, additive schema. No existing tables or rows are dropped.
CREATE TABLE IF NOT EXISTS rice (
    disease_id text PRIMARY KEY,
    source_record_no integer NOT NULL UNIQUE,
    name_en text NOT NULL,
    name_ko text NOT NULL,
    scientific_name text NOT NULL,
    introduction text NOT NULL,
    features jsonb NOT NULL CHECK (jsonb_typeof(features) = 'array'),
    source_conflicts jsonb NOT NULL,
    photo_visible jsonb NOT NULL,
    lab_required jsonb NOT NULL,
    research jsonb NOT NULL,
    raw_features jsonb NOT NULL,
    source_metadata jsonb NOT NULL,
    source_files jsonb NOT NULL,
    content_sha256 text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rice_features_gin ON rice USING gin(features);
CREATE TABLE IF NOT EXISTS maize (
    disease_id text PRIMARY KEY,
    source_record_no integer NOT NULL UNIQUE,
    name_en text NOT NULL,
    name_ko text NOT NULL,
    scientific_name text NOT NULL,
    introduction text NOT NULL,
    features jsonb NOT NULL CHECK (jsonb_typeof(features) = 'array'),
    source_conflicts jsonb NOT NULL,
    photo_visible jsonb NOT NULL,
    lab_required jsonb NOT NULL,
    research jsonb NOT NULL,
    raw_features jsonb NOT NULL,
    source_metadata jsonb NOT NULL,
    source_files jsonb NOT NULL,
    content_sha256 text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS maize_features_gin ON maize USING gin(features);

CREATE TABLE IF NOT EXISTS investigations (
    id uuid PRIMARY KEY,
    crop text NOT NULL CHECK (crop IN ('rice', 'maize')),
    region text NOT NULL,
    observed_date date,
    growth_stage text NOT NULL,
    affected_part text NOT NULL,
    symptoms text NOT NULL,
    status text NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS investigation_photos (
    id uuid PRIMARY KEY,
    investigation_id uuid NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    original_filename text NOT NULL,
    content_type text NOT NULL CHECK (content_type IN ('image/jpeg','image/png','image/webp')),
    size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 10485760),
    width integer NOT NULL CHECK (width > 0),
    height integer NOT NULL CHECK (height > 0),
    sha256 text NOT NULL,
    content bytea NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (octet_length(content) = size_bytes)
);
CREATE INDEX IF NOT EXISTS investigations_created_idx ON investigations(created_at DESC);
CREATE INDEX IF NOT EXISTS investigation_photos_case_idx ON investigation_photos(investigation_id);

-- One current weather snapshot per investigation, including raw provider records.
CREATE TABLE IF NOT EXISTS investigation_weather (
    investigation_id uuid PRIMARY KEY REFERENCES investigations(id) ON DELETE CASCADE,
    location_id bigint NOT NULL,
    status text NOT NULL CHECK (status IN ('partial','unavailable')),
    payload jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
