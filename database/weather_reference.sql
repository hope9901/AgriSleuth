CREATE TABLE IF NOT EXISTS disease_weather_reference (
 disease_id text PRIMARY KEY, crop text NOT NULL CHECK (crop IN ('rice','maize')),
 source_record_no integer NOT NULL, name_en text NOT NULL, name_ko text NOT NULL,
 source_file text NOT NULL, content_sha256 text NOT NULL, source_as_of date NOT NULL,
 profile jsonb NOT NULL, imported_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS disease_weather_window (
 window_id text PRIMARY KEY, disease_id text NOT NULL REFERENCES disease_weather_reference(disease_id),
 anchor text NOT NULL, core boolean NOT NULL, evidence_type text NOT NULL, specification jsonb NOT NULL);
