"""PostgreSQL storage. Credentials stay in environment/local ignored files."""
import hashlib
import os
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from config import load_environment

ROOT = Path(__file__).resolve().parents[1]


def connection_options() -> dict:
    # Do not load or print credentials into logs or a command line.
    load_environment()
    timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT","10"))
    if not 1<=timeout<=30:raise RuntimeError("PostgreSQL connect timeout outside safe bounds.")
    if os.getenv("DATABASE_URL"):
        return {"conninfo": os.environ["DATABASE_URL"], "connect_timeout": timeout}
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    if not all([user, password, db]):
        raise RuntimeError("PostgreSQL credentials are not configured.")
    return dict(host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=user, password=password, dbname=db, connect_timeout=timeout)


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


async def analysis_case(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        cur=await conn.execute('SELECT * FROM investigations WHERE id=%s',(case_id,))
        return await cur.fetchone()

async def claim_analysis(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        cur=await conn.execute("""UPDATE investigations SET status='researching',result=jsonb_set(result,'{status}','"researching"'),updated_at=now()
            WHERE id=%s AND (status NOT IN ('researching','reviewing') OR updated_at < now()-interval '10 minutes') RETURNING id""",(case_id,))
        return await cur.fetchone() is not None

async def update_analysis(case_id,result):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute('UPDATE investigations SET status=%s,result=%s,updated_at=now() WHERE id=%s',(result['status'],Jsonb(result),case_id))

async def fail_analysis(case_id,message):
    case=await analysis_case(case_id)
    if not case:return
    result=case['result'];result.update(status='failed',nextAction=message)
    result.setdefault('limitations',[]).append(message)
    await update_analysis(case_id,result)

async def save_round(case_id,record):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute('INSERT INTO investigation_rounds (investigation_id,payload) VALUES (%s,%s)',(case_id,Jsonb(record)))

async def save_engine(case_id,engine,rounds):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute('INSERT INTO engine_runs (id,investigation_id,payload) VALUES (%s,%s,%s)',(UUID(engine['id']),case_id,Jsonb(engine)))

async def analysis_history(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        rounds=await conn.execute('SELECT payload FROM investigation_rounds WHERE investigation_id=%s ORDER BY id',(case_id,))
        engines=await conn.execute('SELECT payload FROM engine_runs WHERE investigation_id=%s ORDER BY created_at',(case_id,))
        return dict(rounds=[r['payload'] for r in await rounds.fetchall()],engines=[r['payload'] for r in await engines.fetchall()])


async def supplement(case_id,addition):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        cur=await conn.execute('SELECT symptoms,status,result FROM investigations WHERE id=%s FOR UPDATE',(case_id,))
        case=await cur.fetchone()
        if not case:return None
        if case['status'] in ('researching','reviewing'):raise ValueError('Wait for the active investigation to finish.')
        if not addition:raise ValueError('Additional observations must not be blank.')
        symptoms=case['symptoms']+'\nAdditional observations: '+addition
        if len(symptoms)>5000:raise ValueError('Combined symptom observations exceed 5000 characters.')
        result=case['result'];result.update(status='ready',questions=[],summary='Additional observations saved. Start investigation to reassess.',nextAction='Start investigation with the updated observations.')
        await conn.execute('UPDATE investigations SET symptoms=%s,status=%s,result=%s,updated_at=now() WHERE id=%s',(symptoms,'ready',Jsonb(result),case_id))
        return result


async def save_agent_state(run_id,case_id,state):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute("""INSERT INTO agent_runs (id,investigation_id,payload) VALUES (%s,%s,%s)
          ON CONFLICT (id) DO UPDATE SET payload=excluded.payload,updated_at=now()""",(run_id,case_id,Jsonb(state)))

async def read_agent_state(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        cur=await conn.execute('SELECT payload FROM agent_runs WHERE investigation_id=%s ORDER BY created_at DESC LIMIT 1',(case_id,))
        row=await cur.fetchone();return row['payload'] if row else None

async def read_agent_location(case_id):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        cur=await conn.execute('SELECT payload FROM investigation_locations WHERE investigation_id=%s',(case_id,))
        row=await cur.fetchone();return row['payload'] if row else None

async def save_agent_location(case_id,location):
    async with await psycopg.AsyncConnection.connect(**connection_options()) as conn:
        await conn.execute("""INSERT INTO investigation_locations (investigation_id,payload) VALUES (%s,%s)
          ON CONFLICT (investigation_id) DO UPDATE SET payload=excluded.payload,updated_at=now()""",(case_id,Jsonb(location)))


async def weather_references(crop):
    async with await psycopg.AsyncConnection.connect(**connection_options(),row_factory=dict_row) as conn:
        cur=await conn.execute('SELECT disease_id,profile,source_as_of,content_sha256 FROM disease_weather_reference WHERE crop=%s ORDER BY source_record_no',(crop,))
        return await cur.fetchall()
