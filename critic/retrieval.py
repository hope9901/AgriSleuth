"""Read-only evidence retrieval through the real Zetaris SQL API."""
from config import load_environment
load_environment()
import json
import os
import re
from uuid import uuid4
import httpx

class RetrievalError(Exception): pass

async def retrieve(crop):
    if crop not in ('rice','maize'): raise RetrievalError('Unsupported crop.')
    base=os.getenv('ZETARIS_BASE_URL','http://127.0.0.1:3000').rstrip('/')
    username=os.getenv('ZETARIS_USERNAME',''); password=os.getenv('ZETARIS_PASSWORD','')
    table=os.getenv('ZETARIS_EVIDENCE_TABLE','AGRISLEUTH.disease_evidence')
    if not username or not password or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*',table):
        raise RetrievalError('Zetaris configuration is missing or invalid.')
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            login=await client.post(base+'/api/auth/login',json=dict(username=username,password=password));login.raise_for_status()
            session=login.json()
            query=f"SELECT disease_id,name_en,name_ko,scientific_name,feature_no,category,description,source_name,source_urls,source_location,plant_part,growth_stage,source_conflicts FROM {table} WHERE crop = '{crop}' LIMIT 1000"
            response=await client.post(base+'/api/proxy/sql-editor/sqls/run-query',
                headers={'Authorization':'Bearer '+session['idToken'],'X-Org-ID':str(session['orgId']),'X-Request-ID':str(uuid4())},json={'sql':query,'limit':1000})
            response.raise_for_status();data=response.json()
            if data['total']>1000: raise RetrievalError('Evidence retrieval exceeded the row budget.')
            rows=[dict(zip(data['headers'],row)) for row in data['data']]
            for row in rows:
                row['id']=f"{row['disease_id']}_f{row['feature_no']}"
                try:row['urls']=json.loads(row['source_urls'] or '[]')
                except (TypeError,ValueError):row['urls']=[]
                if isinstance(row['urls'],str):row['urls']=[row['urls']]
            return rows
    except (httpx.HTTPError,KeyError,TypeError,ValueError):
        raise RetrievalError('Zetaris evidence retrieval failed. Check platform and source registration.') from None

STOP={'the','and','with','from','this','that','have','leaf','leaves','plant','plants','rice','maize','corn','symptoms','observed'}
TRANSLATIONS={'\ubc18\uc810':'spots','\uac08\uc0c9':'brown','\ub178\ub780':'yellow','\ud669\uc0c9':'yellow','\ub9c8\ub984':'blight','\ud68c\uc0c9':'gray','\ub465\uadfc':'circular','\ud0c0\uc6d0':'elliptical','\uc2dc\ub4e6':'wilt','\uc904\ubb34\ub2ac':'streak','\ub179\ubcd1':'rust','\ub3c4\uc5f4\ubcd1':'blast'}
def rank_evidence(rows, query, excluded=()):
    for ko,en in TRANSLATIONS.items():query += ' '+en if ko in query else ''
    terms={t for t in re.findall(r'[a-z0-9\uac00-\ud7a3]+',query.lower()) if len(t)>2 and t not in STOP}
    scored=[]
    for row in rows:
        if row['id'] in excluded:continue
        if not row.get('description') or not row.get('source_name') or not row.get('urls'):continue
        category=(row.get('category') or '').lower()
        # Search symptom evidence for candidate generation; environment alone is insufficient.
        if not any(t in category for t in ('symptom','sign','diagnos','differential')):continue
        text=' '.join(str(row.get(k) or '') for k in ('description','name_en','name_ko','plant_part')).lower()
        score=sum(1 for term in terms if term in text)
        if score:scored.append((score,row))
    scored.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    selected=[];counts={}
    for score,row in scored:
        disease=row['disease_id']
        if disease not in counts and len(counts)>=3:continue
        if counts.get(disease,0)>=2:continue
        counts[disease]=counts.get(disease,0)+1
        selected.append({**row,'retrieval_score':score})
        if len(selected)>=6:break
    return selected
