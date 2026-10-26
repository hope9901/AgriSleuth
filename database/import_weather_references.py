"""Idempotent import of participant-collected Korean environment references; not source verification."""
import hashlib,json,sys
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
from database import connection_options

def main():
 path=ROOT/'data/diseases/weather_windows.json';data=json.loads(path.read_text())
 assert len({d['no'] for d in data['diseases']})==len(data['diseases'])
 with psycopg.connect(**connection_options()) as conn:
  conn.execute((ROOT/'database/weather_reference.sql').read_text())
  for d in data['diseases']:
   crop={'Rice':'rice','Maize':'maize'}[d['crop']];did=f"{crop}_{d['no']:03d}"
   row=conn.execute(sql.SQL('SELECT scientific_name FROM {} WHERE disease_id=%s').format(sql.Identifier(crop)),(did,)).fetchone()
   if not row or row[0].split()[0].lower()!=d['scientific_name'].split()[0].lower():raise ValueError('Disease mapping requires review: '+did)
   sha=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
   conn.execute("""INSERT INTO disease_weather_reference (disease_id,crop,source_record_no,name_en,name_ko,source_file,content_sha256,source_as_of,profile)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(disease_id) DO UPDATE SET profile=excluded.profile,content_sha256=excluded.content_sha256,source_as_of=excluded.source_as_of,imported_at=now()""",
    (did,crop,d['no'],d['disease_en'],d['disease_ko'],str(path.relative_to(ROOT)),sha,data['as_of'],Jsonb(d)))
   conn.execute('DELETE FROM disease_weather_window WHERE disease_id=%s',(did,))
   for w in d['windows']:
    conn.execute('INSERT INTO disease_weather_window VALUES (%s,%s,%s,%s,%s,%s)',(w['window_id'],did,w['anchor'],w['core'],w['evidence_type'],Jsonb(w)))
  print('Imported references/windows:',conn.execute('SELECT count(*) FROM disease_weather_reference').fetchone()[0],conn.execute('SELECT count(*) FROM disease_weather_window').fetchone()[0])
if __name__=='__main__':main()
