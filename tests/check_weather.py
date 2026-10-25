"""Offline weather checks: synthetic provider fixtures, never fabricated live evidence."""
import asyncio
import os
import sys
from pathlib import Path
from datetime import date,datetime,timezone
from unittest.mock import AsyncMock,patch
from uuid import uuid4
os.environ['LM_STUDIO_MODEL']=''
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'critic'))
import weather
from main import app
from fastapi.testclient import TestClient

start,end,times=weather.observation_times(date(2026,10,24),'Asia/Seoul',datetime(2026,10,25,tzinfo=timezone.utc))
assert start.isoformat()=='2026-10-23T15:00:00+00:00' and len(times)==8
assert all(start<=t<end for t in times)
dst_start,dst_end,dst=weather.observation_times(date(2025,11,2),'America/New_York',datetime(2026,10,25,tzinfo=timezone.utc))
assert (dst_end-dst_start).total_seconds()==25*3600
assert all(dst_start<=t<dst_end for t in dst)
try:weather.observation_times(date(2030,1,1),'UTC')
except weather.WeatherError:pass
else:raise AssertionError('Future day accepted')
assert weather.number('-9',-90,60)==-9
assert weather.number('-99.9',-90,60) is None
assert weather.number('nan',0,100) is None
assert weather.number('',0,100) is None
assert weather.number('0',0,100)==0
print('PASS local/UTC boundaries, DST, future dates, genuine negative temperature, missing/zero values')
stations=weather.parse_stations('# STN LON LAT NAME\n47108 126.97 37.57 SEOUL\n')
assert stations[0]['id']=='47108'
try:weather.parse_stations('<html>access denied</html>')
except weather.WeatherError:pass
else:raise AssertionError('Invalid station header accepted')
instant=datetime(2026,10,24,tzinfo=timezone.utc)
payload={'response':{'header':{'resultCode':'00'},'body':{'totalCount':1,'items':{'item':[{'stnId':'47108','tm':'202610240000','ta':'-9','hm':'75','rn':'0','rnWrchHr':'6'}]}}}}
rows=weather.parse_synop(payload,'47108',instant)
assert rows[0]['temperature_c']==-9 and rows[0]['precipitation_period_hours']==6
payload['response']['body']['items']['item'][0]['stnId']='47109'
try:weather.parse_synop(payload,'47108',instant)
except weather.WeatherError:pass
else:raise AssertionError('Wrong station accepted')
print('PASS strict station header and station/time provenance checks')
diseases=[dict(disease_id='maize_013',name_en='test',source_conflicts=[],features=[dict(category='Timing of occurrence (environment)',description='Favored by leaf wetness over 6 hours and 18–27 °C (64–81 °F).',source_name='CPN Encyclopedia NCLB',url=['https://example.org'],location_in_source='test')])]
comparison=weather.compare_conditions(diseases,{'observations':[{'temperature_c':20},{'temperature_c':30}]})
assert comparison[0]['temperature_check']['samples_in_range']==1
assert comparison[0]['assessment']=='manual_review_required'
diseases[0]['source_conflicts']=['unresolved']
assert weather.compare_conditions(diseases,{'observations':[{'temperature_c':20}]})[0]['temperature_check'] is None
print('PASS source-gated temperature comparison and conflict abstention')
case=dict(crop='maize',region='Seoul',observed_date=date(2026,10,24))
case_id=str(uuid4())
with TestClient(app) as client:
 with patch('main.weather_case',AsyncMock(return_value=(case,diseases))),patch('main.fetch_weather',AsyncMock(side_effect=weather.WeatherError('Test unavailable'))),patch('main.save_weather',AsyncMock()) as save:
  response=client.post(f'/api/investigations/{case_id}/weather',json={'location_id':1})
  assert response.status_code==200,response.text
  assert response.json()['status']=='unavailable' and response.json()['comparisons']==[]
  save.assert_awaited_once()
 with patch('main.weather_case',AsyncMock(return_value=(None,[]))):
  assert client.post(f'/api/investigations/{case_id}/weather',json={'location_id':1}).status_code==404
 assert client.post(f'/api/investigations/{case_id}/weather',json={'location_id':-1}).status_code==422
 with patch('main.search_locations',AsyncMock(side_effect=weather.WeatherError('Provider unavailable'))):
  assert client.get('/api/weather/locations?q=Seoul').status_code==502
print('PASS unavailable evidence persistence, missing case, invalid ID and geocoding failure contracts')

# Execute the actual transport/orchestration with an explicitly synthetic provider.
OriginalClient=weather.httpx.AsyncClient
import httpx
async def fake_provider(request):
 if request.url.host=='geocoding-api.open-meteo.com':
  return httpx.Response(200,json=dict(id=1,name='Synthetic',latitude=37.57,longitude=126.97,timezone='Asia/Seoul'))
 if request.url.path.endswith('stn_gts1.php'):
  return httpx.Response(200,text='# STN LON LAT\n47108 126.97 37.57\n')
 return httpx.Response(200,json={'response':{'header':{'resultCode':'00'},'body':{'totalCount':1,'items':{'item':[dict(stnId='47108',tm=request.url.params['tm'],ta=20,hm=80,rn=1,rnWrchHr=6)]}}}})
async def run():
 with patch.dict(os.environ,{'KMA_AUTH_KEY':'SYNTHETIC-TEST-KEY'}),patch('weather.httpx.AsyncClient',lambda **kw:OriginalClient(transport=httpx.MockTransport(fake_provider),**kw)):
  report=await weather.fetch_weather(1,date(2026,10,24))
  assert len(report['observations'])==8 and report['summary']['sample_count']==8
  assert report['station']['distance_km']==0
  assert 'SYNTHETIC-TEST-KEY' not in str(report)
  assert 'precipitation_total' not in report['summary']
asyncio.run(run())
print('PASS mocked provider integration, eight local-day timestamps, key redaction and no rain summation')
print('All weather checks passed. Live KMA authorization still requires verification.')
