"""Register the JDBC evidence view. No passwords or provider response bodies are logged."""
import argparse
import secrets
import sys
from pathlib import Path
from uuid import uuid4
import httpx
import psycopg
from psycopg import sql
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'critic'))
from database import connection_options

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--platform-env',type=Path,help='Optional local Zetaris platform .env (never committed)')
    args=parser.parse_args()
    env=ROOT/'critic/.env';local=dotenv_values(env)
    platform=dotenv_values(args.platform_env) if args.platform_env else {}
    username=local.get('ZETARIS_USERNAME') or platform.get('ZETARIS_ADMIN_EMAIL')
    password=local.get('ZETARIS_PASSWORD') or platform.get('ZETARIS_ADMIN_PASSWORD')
    if not username or not password:raise SystemExit('Set Zetaris credentials in critic/.env.')
    source_password=local.get('ZETARIS_SOURCE_PASSWORD') or secrets.token_urlsafe(24)
    with psycopg.connect(**connection_options()) as conn:
        conn.execute((ROOT/'database/evidence_view.sql').read_text())
        exists=conn.execute("SELECT 1 FROM pg_roles WHERE rolname='agrisleuth_reader'").fetchone()
        if not exists:conn.execute(sql.SQL('CREATE ROLE agrisleuth_reader LOGIN PASSWORD {}').format(sql.Literal(source_password)))
        elif not local.get('ZETARIS_SOURCE_PASSWORD'):raise SystemExit('Existing reader role has no recorded credential; refusing to reset it.')
        conn.execute('GRANT USAGE ON SCHEMA public TO agrisleuth_reader')
        conn.execute('GRANT SELECT ON disease_evidence TO agrisleuth_reader')
    values=dict(ZETARIS_BASE_URL=local.get('ZETARIS_BASE_URL') or 'http://127.0.0.1:3000',ZETARIS_USERNAME=username,ZETARIS_PASSWORD=password,ZETARIS_SOURCE_PASSWORD=source_password,ZETARIS_EVIDENCE_TABLE='AGRISLEUTH.disease_evidence')
    text=env.read_text() if env.exists() else ''
    for key,value in values.items():
        if key not in local:text+='\n'+key+'='+value
    env.write_text(text+'\n');env.chmod(0o600)
    with httpx.Client(base_url=values['ZETARIS_BASE_URL'],timeout=90) as client:
        response=client.post('/api/auth/login',json=dict(username=username,password=password));response.raise_for_status();session=response.json()
        headers={'Authorization':'Bearer '+session['idToken'],'X-Org-ID':str(session['orgId']),'X-Request-ID':str(uuid4())}
        def query(statement):
            response=client.post('/api/proxy/sql-editor/sqls/run-query',headers=headers,json=dict(sql=statement,limit=1000))
            if response.status_code!=200:raise SystemExit('Zetaris SQL failed. Check registration in the local UI; raw response suppressed.')
            return response.json()
        sources=query('SHOW DATASOURCES')
        if not any(row[0]=='AGRISLEUTH' for row in sources['data']):
            # Only setup-generated URL-safe credentials enter the quoted SQL here.
            import re
            if not re.fullmatch(r'[A-Za-z0-9_-]+',source_password):raise SystemExit('Invalid source credential characters.')
            query('CREATE DATASOURCE AGRISLEUTH DESCRIBE BY "AgriSleuth read-only disease evidence" OPTIONS (jdbcdriver "org.postgresql.Driver", jdbcurl "jdbc:postgresql://host.docker.internal:5432/agrisleuth", username "agrisleuth_reader", password "'+source_password+'", schema "public")')
            query('REGISTER DATASOURCE TABLE "disease_evidence" FROM AGRISLEUTH')
        result=query('SELECT disease_id FROM AGRISLEUTH.disease_evidence LIMIT 1')
        if not result.get('data'):raise SystemExit('Evidence view returned no rows.')
    print('Zetaris read-only JDBC disease evidence query passed.')
if __name__=='__main__':main()
