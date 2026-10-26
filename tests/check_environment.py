import asyncio,json,sys,os
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
from environment import evaluate_environment
from weather import country_stations,WeatherError
import database,httpx
async def main():
 refs=await database.weather_references('rice');assert len(refs)==12
 live=json.loads((ROOT/'docs/weather-live-2026-10-26.json').read_text())['additional_reports'][0]
 result=evaluate_environment(refs,live);blast=next(a for a in result if a['disease_id']=='rice_001')
 assert len(result)==12 and blast['assessment']=='insufficient_for_infection_assessment'
 assert all(w['coverage']!='dates_covered' for w in blast['windows'] if w['anchor']=='D')
 assert next(c for c in blast['checks'] if 'humidity' in c['metric'])['valid_samples']==sum(row.get('humidity_pct') is not None for row in live['observations'])
 assert '90%' not in str(blast.get('infection_probability',''))
 assert all(a['sources'] for a in result)
 empty=evaluate_environment(refs,dict(observed_date='2026-07-18',observations=[]))
 assert all(c['valid_samples']==0 for a in empty for c in a['checks'])
 moved=dict(live,case_observed_date='2026-07-20')
 assert evaluate_environment(refs,moved)[0]['windows'][0]['end_date']=='2026-07-16'
 from copy import deepcopy
 changed=deepcopy(refs);changed[0]['profile']['thresholds_text']='No numerical criteria verified'
 assert not evaluate_environment(changed,live)[0]['checks']
 print('PASS real reference DB 12 rice profiles, English provenance, incomplete window and missing-value abstention')
 original=httpx.AsyncClient
 async def fake(request):
  page=int(request.url.params['pageNo']); ids=range(10000,10100) if page==1 else [10100]
  items=''.join(f'<item><stnId>{i}</stnId><countryName>TEST</countryName><stnNm>S</stnNm></item>' for i in ids)
  return httpx.Response(200,text=f'<response><header><resultCode>00</resultCode></header><body><items>{items}</items><totalCount>101</totalCount></body></response>')
 with patch.dict(os.environ,{'KMA_AUTH_KEY':'TEST-ONLY'}),patch('weather.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(fake),**kw)):
  data=await country_stations('1001');assert data['total_count']==101 and len(data['stations'])==101
  assert 'TEST-ONLY' not in str(data)
 print('PASS country XML pagination and key exclusion (explicit synthetic provider)')
asyncio.run(main())
