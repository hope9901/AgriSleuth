"""Load the current JSON sources without dropping data. Run from any directory."""
import hashlib
import json
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "critic"))
from database import connection_options

SOURCES = {
    "rice": ("rice", "Rice disease features.json", "rice_disease_research.json"),
    "maize": ("corn", "Maize disease features.json", "corn_disease_research.json"),
}


def source_records():
    result = []
    for table, (folder, features_name, research_name) in SOURCES.items():
        fp = ROOT / "data/diseases" / folder / features_name
        rp = ROOT / "data/diseases" / folder / research_name
        features = json.loads(fp.read_text(encoding="utf-8"))
        research = json.loads(rp.read_text(encoding="utf-8"))
        records = {d["no"]: d for d in research["diseases"]}
        numbers = [d["no"] for d in features["diseases"]]
        if len(records) != len(research["diseases"]) or len(numbers) != len(set(numbers)):
            raise ValueError(f"Duplicate source numbers in {table}")
        if set(numbers) != set(records):
            raise ValueError(f"Feature/research records do not match in {table}")
        metadata = {
            "features": {k: v for k, v in features.items() if k != "diseases"},
            "research": {k: v for k, v in research.items() if k != "diseases"},
        }
        paths = [str(fp.relative_to(ROOT)), str(rp.relative_to(ROOT))]
        for feature in features["diseases"]:
            report = records[feature["no"]]
            payload = {"features": feature, "research": report, "metadata": metadata}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            result.append((table, (
                f"{table}_{feature['no']:03d}", feature["no"], feature["name_en"],
                feature["name_ko"], feature["scientific_name"], feature.get("intro", ""),
                Jsonb(feature.get("features", [])), Jsonb(feature.get("source_conflicts", [])),
                Jsonb(feature.get("photo_visible", [])), Jsonb(feature.get("lab_required", [])),
                Jsonb(report), Jsonb(feature), Jsonb(metadata), Jsonb(paths), digest,
            )))
    return result


def main():
    records = source_records()  # Validate every file before touching the DB.
    columns = ["disease_id", "source_record_no", "name_en", "name_ko", "scientific_name",
               "introduction", "features", "source_conflicts", "photo_visible", "lab_required",
               "research", "raw_features", "source_metadata", "source_files", "content_sha256"]
    with psycopg.connect(**connection_options()) as conn:
        conn.execute((ROOT / "database/schema.sql").read_text())
        for table, values in records:
            updates = sql.SQL(",").join(sql.SQL("{}=EXCLUDED.{}").format(sql.Identifier(c),sql.Identifier(c))
                                      for c in columns[1:])
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (disease_id) "
                                "DO UPDATE SET {}, imported_at=now() "
                                "WHERE {}.content_sha256 IS DISTINCT FROM EXCLUDED.content_sha256").format(
                sql.Identifier(table),sql.SQL(",").join(map(sql.Identifier, columns)),
                sql.SQL(",").join(sql.Placeholder() for _ in columns),updates,sql.Identifier(table))
            conn.execute(statement, values)
        for table in SOURCES:
            row = conn.execute(sql.SQL("SELECT count(*),sum(jsonb_array_length(features)) FROM {}").format(
                sql.Identifier(table))).fetchone()
            print(f"{table}: {row[0]} diseases; {row[1]} features")
    print("Committed schema and disease import. Existing unrelated records were preserved.")


if __name__ == "__main__":
    main()
