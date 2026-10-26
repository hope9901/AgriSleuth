"""One attributed sample + constructed metadata; no accuracy estimate or model mocks."""
import httpx,time,json
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parents[1]
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as c:
 data=dict(crop='rice',region='Seoul',observed_date='2026-07-18',growth_stage='vegetative',affected_part='leaf',symptoms='Spindle-shaped leaf lesions with gray-white centers and brown margins. Investigate a tentative hypothesis. Please check whether the observed-day humidity and temperature overlap the source environment references, and explain any missing infection-window measurements. The city and observation date are provided; do not treat weather overlap as proof of infection.')
 resp=c.post('/api/investigations',data=data,files={'photo':('rice-blast-usda-d542-1.jpg',(r/'web_developer/public/samples/rice-blast-usda-d542-1.jpg').read_bytes(),'image/jpeg')});resp.raise_for_status();cid=resp.json()['id'];print('CASE',cid,flush=True)
 resp=c.post(f'/api/investigations/{cid}/location',json={'location_id':1835848});resp.raise_for_status()
 resp=c.post(f'/api/investigations/{cid}/run');resp.raise_for_status();start=time.monotonic();previous=None
 while time.monotonic()-start<560:
  time.sleep(5)
  resp=c.get(f'/api/investigations/{cid}');resp.raise_for_status();result=resp.json();phase=(result['status'],result['events'][-1]['node'] if result.get('events') else '')
  if phase!=previous:print('PROGRESS',round(time.monotonic()-start,1),phase,flush=True);previous=phase
  if result['status'] not in ('researching','reviewing'):break
 agent=c.get(f'/api/investigations/{cid}/agent');agent.raise_for_status();agent=agent.json();weather=c.get(f'/api/investigations/{cid}/weather');history=c.get(f'/api/investigations/{cid}/history')
 expected='rice_001';actual=[h.get('id') for h in result.get('hypotheses',[])]
 export=dict(checked_at=datetime.now(timezone.utc).isoformat(),case_id=cid,elapsed_seconds=round(time.monotonic()-start,1),input=data,sample='web_developer/public/samples/rice-blast-usda-d542-1.jpg',expected_from_sample_label=expected,ground_truth_independently_verified=False,measurement_scope='One attributed sample with constructed symptom text and location/date. Not image-only evaluation or diagnostic accuracy.',expected_label_present=expected in actual,result=result,agent=agent,weather=weather.json() if weather.status_code==200 else None,history=history.json())
 (r/'docs/environment-sample-latest.json').write_text(json.dumps(export,ensure_ascii=False,indent=2));print('END',cid,result['status'],actual,export['elapsed_seconds'],[(t['tool'],t['status']) for t in agent['tool_history']],flush=True)
