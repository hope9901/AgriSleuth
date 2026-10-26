import os,sys
from pathlib import Path
from io import BytesIO
from unittest.mock import AsyncMock, patch
os.environ['LM_STUDIO_MODEL']=''
sys.dont_write_bytecode=True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'critic'))
from fastapi.testclient import TestClient
from PIL import Image
import main as api
from main import app, build_review_graph
from schemas import CriticReview
from critic import load_prompt

image=BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG');payload=image.getvalue()
base={'crop':'rice','region':'Gimje','observed_date':'2026-10-24','symptoms':'Leaf spots', 'growth_stage':'vegetative','affected_part':'leaf'}
api.save_investigation = AsyncMock()  # Offline contract test; no DB writes.
keys={'photoId','id','status','summary','questions','hypotheses','evidence','reviewIssues','nextAction','limitations','events'}
with TestClient(app) as c:
 r=c.post('/api/investigations',data=base,files={'photo':('test.png',payload,'image/png')})
 assert r.status_code==200,r.text
 data=r.json();assert keys==set(data);assert data['status']=='ready';assert data['hypotheses']==[]
 assert [e['node'] for e in data['events']]==['validate_upload','validate_input','prepare']
 print('PASS multipart contract and actual events')
 r=c.post('/api/investigations',data={**base,'symptoms':' '},files={'photo':('test.png',payload,'image/png')})
 assert r.status_code==200 and r.json()['status']=='ready';print('PASS optional missing observations')
 r=c.post('/api/investigations',data=base,files={'photo':('fake.png',b'not an image','image/png')})
 assert r.status_code==422;print('PASS invalid image')
 r=c.post('/api/investigations',data=base,files={'photo':('test.jpg',payload,'image/jpeg')})
 assert r.status_code==415;print('PASS mismatched MIME')
 r=c.post('/api/investigations',data={'crop':'rice'},files={'photo':('photo-only.png',payload,'image/png')})
 assert r.status_code==200 and r.json()['status']=='ready';print('PASS photograph-only upload')
 r=c.post('/api/investigations',data={'crop':'rice'})
 assert r.status_code==422;print('PASS missing photograph rejected')
 r=c.post('/api/investigations',data={**base,'observed_date':'bad-date'},files={'photo':('test.png',payload,'image/png')})
 assert r.status_code==422;print('PASS invalid date')
 r=c.post('/api/investigations',data=base,files={'photo':('big.png',b'x'*(10*1024*1024+1),'image/png')})
 assert r.status_code==413;print('PASS oversized upload')
 r=c.options('/api/investigations',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
 assert r.headers['access-control-allow-origin']=='http://localhost:5173';print('PASS browser CORS')
 review={'crop':'rice','observations':'Synthetic test','candidates':[{'id':'c1','name':'Synthetic A','claim':'Possible A','evidence_ids':['e1']}], 'evidence':[{'id':'e1','text':'Synthetic evidence','source':'Fixture','location':'1'}]}
 assert c.post('/api/reviews',json=review).status_code==503;print('PASS unconfigured Critic does not pass')
 class FakeReviewer:
  async def ainvoke(self,messages):
   return CriticReview(issues=[],limitations=['Synthetic review only'],review_summary='Synthetic response')
 app.state.review_graph=build_review_graph(FakeReviewer())
 r=c.post('/api/reviews',json=review)
 assert r.status_code==200,r.text
 assert r.json()['action']=='finalize_with_limitations' and r.json()['trace']==['critic','judge'];print('PASS review graph with explicitly mocked model')
 assert c.post('/api/reviews',json={**review,'candidates':[]}).json()['action']=='retrieve_evidence';print('PASS empty evidence gate')
 p=load_prompt();assert 'Implement the initial' not in p and '## Output rules' in p;print('PASS runtime-only Markdown prompt')
print('All intake and review checks passed. No live model or weather calls performed.')

# Starting a saved photograph-only case must not demand optional metadata.
from uuid import uuid4
case_id=uuid4()
with TestClient(app) as c:
 with patch('main.analysis_case',AsyncMock(return_value={'result':{'photoId':str(uuid4())}})),patch('main.claim_analysis',AsyncMock(return_value=True)),patch('main.execute',AsyncMock()):
  response=c.post(f'/api/investigations/{case_id}/run')
  assert response.status_code==202,response.text
print('PASS photograph-only start accepts missing optional metadata (mocked execution)')
