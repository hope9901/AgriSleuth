"""Verify weather snapshots in a disposable PostgreSQL schema."""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'critic'))
import database
import psycopg
from psycopg import sql
options=database.connection_options()
schema='agrisleuth_weather_check_'+uuid4().hex
case_id=uuid4()
with psycopg.connect(**options,autocommit=True) as admin:
 admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
 try:
  test_options={**options,'options':f'-c search_path={schema}'}
  database.connection_options=lambda:test_options
  with psycopg.connect(**test_options) as conn:
   conn.execute((ROOT/'database/schema.sql').read_text())
   conn.execute("INSERT INTO investigations (id,crop,region,observed_date,growth_stage,affected_part,symptoms,status,result) VALUES (%s,'rice','Synthetic','2026-10-24','','','','ready','{}')",(case_id,))
  async def check():
   payload=dict(status='partial',observations=[dict(temperature_c=20,raw=dict(ta='20'))],comparisons=[])
   await database.save_weather(case_id,1,payload)
   assert await database.read_weather(case_id)==payload
   payload['status']='unavailable';payload['observations']=[]
   await database.save_weather(case_id,2,payload)
   assert await database.read_weather(case_id)==payload
   try:await database.save_weather(uuid4(),1,payload)
   except psycopg.errors.ForeignKeyViolation:pass
   else:raise AssertionError('Orphan snapshot accepted')
  asyncio.run(check())
  with psycopg.connect(**test_options) as conn:
   assert conn.execute('SELECT count(*) FROM investigation_weather').fetchone()[0]==1
  print('PASS real PostgreSQL snapshot round-trip, replacement and foreign-key protection')
 finally:
  admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
print('Disposable schema cleaned; application investigations untouched.')
