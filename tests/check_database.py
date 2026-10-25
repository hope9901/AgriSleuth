"""Real PostgreSQL checks in an isolated disposable schema. No model calls."""
import hashlib
import os
import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4

os.environ["LM_STUDIO_MODEL"] = ""
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "critic"))
import psycopg
from psycopg import sql
from fastapi.testclient import TestClient
from PIL import Image
import database
from main import app

options = database.connection_options()
schema = "agrisleuth_check_" + uuid4().hex
with psycopg.connect(**options, autocommit=True) as admin:
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        test_options = {**options, "options": f"-c search_path={schema}"}
        database.connection_options = lambda: test_options
        with psycopg.connect(**test_options) as conn:
            conn.execute((ROOT / "database/schema.sql").read_text())
        image = BytesIO()
        Image.new("RGB", (3, 2)).save(image, format="PNG")
        photo = image.getvalue()
        fields = dict(crop="maize", region="Synthetic location", observed_date="2026-10-24",
                      growth_stage="vegetative", affected_part="leaf", symptoms="Synthetic spots")
        with TestClient(app) as client:
            response = client.post("/api/investigations", data=fields,
                                   files={"photo": ("synthetic.png", photo, "image/png")})
            assert response.status_code == 200, response.text
            result = response.json()
            assert client.get(f"/api/investigations/{result['id']}").json() == result
            downloaded = client.get(f"/api/photos/{result['photoId']}")
            assert downloaded.status_code == 200 and downloaded.content == photo
            assert downloaded.headers["content-type"] == "image/png"
            print("PASS real upload, persisted result and exact photo retrieval")
            with psycopg.connect(**test_options) as conn:
                row = conn.execute("SELECT crop,growth_stage,affected_part FROM investigations").fetchone()
                assert row == ("maize", "vegetative", "leaf")
                row = conn.execute("SELECT width,height,sha256 FROM investigation_photos").fetchone()
                assert row == (3, 2, hashlib.sha256(photo).hexdigest())
            print("PASS observation context and image metadata")
            assert client.get(f"/api/investigations/{uuid4()}").status_code == 404
            assert client.get(f"/api/photos/{uuid4()}").status_code == 404
            print("PASS missing record handling")
            # Deliberately fail the photo insert to verify the investigation rolls back.
        with psycopg.connect(**test_options) as conn:
            conn.execute("ALTER TABLE investigation_photos ADD CONSTRAINT reject_test_photo CHECK (false) NOT VALID")
        with TestClient(app) as client:
            response = client.post("/api/investigations", data=fields,
                                   files={"photo": ("synthetic.png", photo, "image/png")})
            assert response.status_code == 503, response.text
        with psycopg.connect(**test_options) as conn:
            assert conn.execute("SELECT count(*) FROM investigations").fetchone()[0] == 1
            assert conn.execute("SELECT count(*) FROM investigation_photos").fetchone()[0] == 1
        print("PASS failed photo insert rolls back the investigation")
    finally:
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        print("Removed disposable test schema; public application records untouched.")
