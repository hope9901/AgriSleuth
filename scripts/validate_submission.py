"""Real API/LM/Zetaris/Meterless demonstrations. No provider mocks, no accuracy labels."""
import argparse,json,time,sys
from pathlib import Path
from datetime import datetime,timezone
from io import BytesIO
import httpx
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission';OUT.mkdir(exist_ok=True)
CASES=[dict(name='supported-rice-hypothesis',crop='rice',region='Gimje-si, Jeonbuk',observed_date='2026-07-18',growth_stage='vegetative',affected_part='leaf',symptoms='Several leaf lesions are spindle or eye shaped, with gray-white centers and brown margins. Lesions extend along the leaf blade; no circular evenly brown spots or vein-limited rectangular lesions were observed. Please investigate a tentative source-supported hypothesis, not a confirmed diagnosis.'),dict(name='insufficient-observation',crop='maize',region='Hongcheon-gun, Gangwon',observed_date='2026-08-09',growth_stage='unknown',affected_part='leaf',symptoms='Leaves look discolored. Lesion shape, size, distribution and progression cannot be determined. No distinguishing symptom has been confirmed. Please ask for the observations needed before proposing a disease.')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['all','normal','uncertain'],default='all');args=parser.parse_args()
    output=OUT/'live-validation.json'
    report=json.loads(output.read_text()) if output.exists() else dict(track='Track 2 - The Agent That Can Explain Why',input_type='Constructed software demonstrations with an attributed rice sample / synthetic low-information image; not labeled diagnostic evaluation',cases=[])
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
      for index,case in enumerate(CASES):
        if args.case=='normal' and index!=0 or args.case=='uncertain' and index!=1:continue
        if index==0:content=(ROOT/'web_developer/public/samples/rice-blast-usda-d542-1.jpg').read_bytes();filename='rice-sample.jpg';mime='image/jpeg'
        else:
          buffer=BytesIO();Image.new('RGB',(128,128),(125,128,122)).save(buffer,format='PNG');content=buffer.getvalue();filename='synthetic-uninformative.png';mime='image/png'
        data={k:v for k,v in case.items() if k!='name'}
        response=client.post('/api/investigations',data=data,files={'photo':(filename,content,mime)});response.raise_for_status();case_id=response.json()['id']
        item=dict(name=case['name'],id=case_id,started_at=datetime.now(timezone.utc).isoformat(),input=data,input_type='constructed demonstration, not ground truth',status='running',viewer_url=f'http://127.0.0.1:5173/?investigation={case_id}&demo=1')
        report['cases']=[r for r in report['cases'] if r['name']!=case['name']]+[item];output.write_text(json.dumps(report,indent=2)+'\n')
        print('START',case['name'],case_id,flush=True)
        start=time.monotonic();response=client.post(f'/api/investigations/{case_id}/run');response.raise_for_status();previous=None;read_errors=0
        while time.monotonic()-start<570:
          time.sleep(5)
          try:
            response=client.get(f'/api/investigations/{case_id}');response.raise_for_status();result=response.json()
          except httpx.HTTPError:
            read_errors+=1
            if read_errors>5:raise
            print('Read retry',read_errors,flush=True);continue
          phase=(result['status'],result['events'][-1]['node'] if result.get('events') else '')
          if phase!=previous:print('PROGRESS',case['name'],phase,round(time.monotonic()-start,1),flush=True);previous=phase
          if result['status'] not in ('researching','reviewing'):break
        agent=client.get(f'/api/investigations/{case_id}/agent');agent.raise_for_status();state=agent.json()
        history=client.get(f'/api/investigations/{case_id}/history');history.raise_for_status()
        item.update(status=result['status'],elapsed_seconds=round(time.monotonic()-start,1),read_retries=read_errors,hypotheses=result['hypotheses'],questions=result['questions'],finish_reason=state.get('finish_reason'),tools=[{k:t.get(k) for k in ('tool','reason','status','summary','error_code')} for t in state['tool_history']],judge_decisions=state['judge_decisions'],source_ids=[e['id'] for e in result['evidence']],engine_runs=len(history.json()['engines']))
        item['checks']=dict(terminal=result['status'] in ('completed','needs_more_evidence','abstained','failed'),real_zetaris_search=any(t['tool']=='search_diseases' and t['status']=='completed' for t in state['tool_history']),verified=any(t['tool']=='verify_evidence' and t['status']=='completed' for t in state['tool_history']),no_false_completion=result['status']!='completed' or bool(state.get('verified_fingerprint')),questions_or_abstention=result['status'] in ('needs_more_evidence','abstained'))
        (OUT/(case['name']+'.json')).write_text(json.dumps(dict(input=item,result=result,agent=state,history=history.json()),indent=2)+'\n')
        output.write_text(json.dumps(report,indent=2)+'\n');print('END',json.dumps(item,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
