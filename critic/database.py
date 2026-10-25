"""PostgreSQL storage. Credentials stay in environment/local ignored files."""
import hashlib
import os
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def connection_options() -> dict:
    # Do not load or print credentials into logs or a command line.
    local = dotenv_values(ROOT / "data" / ".env.postgres")
    if os.getenv("DATABASE_URL"):
        return {"conninfo": os.environ["DATABASE_URL"], "connect_timeout": 5}
    user = os.getenv("POSTGRES_USER") or local.get("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD") or local.get("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB") or local.get("POSTGRES_DB")
    if not all([user, password, db]):
        raise RuntimeError("PostgreSQL credentials are not configured.")
    return dict(host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=user, password=password, dbname=db, connect_timeout=5)


async def save_investigation(*, result, crop, region, observed_date,
                             growth_stage, affected_part, symptoms,
                             photo_id, filename, content_type, width, height, contents):
    # One transaction: no orphaned photo or partially saved investigation.
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute(
            """INSERT INTO investigations
               (id,crop,region,observed_date,growth_stage,affected_part,symptoms,status,result)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (UUID(result.id),crop,region,observed_date,growth_stage,affected_part,
             symptoms,result.status,Jsonb(result.model_dump(mode="json"))),
        )
        await conn.execute(
            """INSERT INTO investigation_photos
               (id,investigation_id,original_filename,content_type,size_bytes,width,height,sha256,content)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (UUID(photo_id),UUID(result.id),Path(filename or "upload").name,
             content_type,len(contents),width,height,hashlib.sha256(contents).hexdigest(),contents),
        )


async def get_investigation(case_id: UUID):
    async with await psycopg.AsyncConnection.connect(
        **connection_options(), row_factory=dict_row
    ) as conn:
        cursor = await conn.execute("SELECT result FROM investigations WHERE id=%s", (case_id,))
        row = await cursor.fetchone()
        return row["result"] if row else None


async def get_photo(photo_id: UUID):
    async with await psycopg.AsyncConnection.connect(
        **connection_options(), row_factory=dict_row
    ) as conn:
        cursor = await conn.execute(
            "SELECT content,content_type FROM investigation_photos WHERE id=%s", (photo_id,)
        )
        return await cursor.fetchone()


async def weather_case(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(), row_factory=dict_row) as conn:
        cur = await conn.execute("SELECT crop,region,observed_date FROM investigations WHERE id=%s", (case_id,))
        case = await cur.fetchone()
        if not case: return None, []
        # Table identifiers come only from the database crop check constraint.
        from psycopg import sql
        cur = await conn.execute(sql.SQL("SELECT disease_id,name_en,features,source_conflicts FROM {} ORDER BY source_record_no").format(sql.Identifier(case['crop'])))
        return case, await cur.fetchall()

async def save_weather(case_id, location_id, report):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute("""INSERT INTO investigation_weather (investigation_id,location_id,status,payload)
            VALUES (%s,%s,%s,%s) ON CONFLICT (investigation_id) DO UPDATE SET
            location_id=excluded.location_id,status=excluded.status,payload=excluded.payload,updated_at=now()""",
            (case_id,location_id,report['status'],Jsonb(report)))

async def read_weather(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(), row_factory=dict_row) as conn:
        cur = await conn.execute("SELECT payload FROM investigation_weather WHERE investigation_id=%s",(case_id,))
        row = await cur.fetchone()
        return row['payload'] if row else None
