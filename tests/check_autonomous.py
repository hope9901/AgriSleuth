"""A-G: real PostgreSQL + real Meterless; explicitly mocked LLM/tool providers."""
import os,sys,asyncio,shutil,json
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock,patch
os.environ['AGENT_MAX_ITERATIONS']='5';os.environ['AGENT_DEADLINE_SECONDS']='480';os.environ['LM_STUDIO_MODEL']='fixture';os.environ['NODE_BINARY']=shutil.which('node') or 'node'
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
import database,agent_runtime,agent_tools,pipeline
from agent_controller import ToolDecision
from agent_tools import FinishArgs
from pipeline import Proposal
from schemas import Candidate,CriticIssue,CriticReview
from vision import ImageObservations
from evaluation import compare_modes
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from datetime import date
from fastapi.testclient import TestClient
from main import app
rows=[dict(id='maize_013_f1',disease_id='maize_013',name_en='Northern corn leaf blight',description='Long cigar gray lesions crossing leaf veins',category='Symptoms - leaf',source_name='Synthetic source',source_location='Fixture',urls=['https://example.org/fixture'],source_conflicts='[]')]
proposal=Proposal(candidates=[Candidate(id='maize_013',name='Northern corn leaf blight',claim='Tentative symptom resemblance',evidence_ids=['maize_013_f1'])],summary='Fixture hypothesis',limitations=['Not a real diagnosis'])
def decision(tool,**arguments):return ToolDecision(tool=tool,reason='Synthetic decision rationale for '+tool,arguments=arguments)
def finish(status='abstained'):return decision('finish_investigation',status=status,reason='Fixture stopping reason',questions=['Check lesion underside'] if status=='needs_more_evidence' else [],uncertainties=['Fixture uncertainty'],final_candidate_ids=[])
def critic(block=False):
 return CriticReview(issues=[CriticIssue(code='OBSERVATION_MISMATCH',severity='blocking',candidate_id='maize_013',reason='Distinguishing underside feature is not visible',evidence_ids=['maize_013_f1'],suggested_action='retrieve_evidence',requested_information='Inspect the leaf underside')] if block else [],limitations=['Synthetic uncertainty'],review_summary='Fixture contradiction' if block else 'Fixture review passed')
options=database.connection_options();schema='agrisleuth_autonomous_'+uuid4().hex
with psycopg.connect(**options,autocommit=True) as admin:
 admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
 try:
  local={**options,'options':f'-c search_path={schema}'};database.connection_options=lambda:local
  with psycopg.connect(**local) as conn:conn.execute((ROOT/'database/schema.sql').read_text())
  def seed():
   case_id=uuid4();result=dict(id=str(case_id),photoId=str(uuid4()),status='ready',summary='Synthetic',questions=[],hypotheses=[],evidence=[],reviewIssues=[],nextAction=None,limitations=[],events=[])
   with psycopg.connect(**local) as conn:conn.execute("INSERT INTO investigations (id,crop,region,observed_date,growth_stage,affected_part,symptoms,status,result) VALUES (%s,'maize','Synthetic','2026-10-24','','leaf','cigar gray lesions','ready',%s)",(case_id,Jsonb(result)))
   return case_id
  async def run(actions,reviews=(),generated=None):
   case_id=seed()
   import copy
   snapshots=[];choices=iter(actions)
   async def select(state,carryover):
    snapshots.append(copy.deepcopy(state));return next(choices)
   choose=AsyncMock(side_effect=select);choose.snapshots=snapshots
   with patch('agent_runtime.select_action',choose),patch('agent_tools.retrieve',AsyncMock(return_value=rows)) as retrieve,patch('pipeline.generate',AsyncMock(return_value=generated or proposal)),patch('agent_tools.call_critic_agent',AsyncMock(side_effect=reviews)),patch('agent_tools.database.get_photo',AsyncMock(return_value={'content':b'fixture'})),patch('agent_tools.observe_photo',AsyncMock(return_value=ImageObservations(visible_findings=['Underside cannot be observed'],limitations=['Additional photo required']))):
    await database.claim_analysis(case_id);await agent_runtime.execute(case_id)
   state=await database.read_agent_state(case_id);result=await database.analysis_case(case_id)
   assert result['status']==state['status'],result
   return case_id,state,retrieve.call_count,choose
  async def main():
   # A: missing weather -> policy chooses actual weather tool, not fixed orchestration.
   weather=dict(status='partial',location=dict(id=1,label='Fixture',latitude=37.,longitude=127.,timezone='Asia/Seoul'),observed_date='2026-10-24',observations=[dict(temperature_c=20)],summary={'sample_count':1},limitations=[])
   with patch('agent_tools.search_locations',AsyncMock(return_value=[weather['location']])),patch('agent_tools.fetch_weather',AsyncMock(return_value=weather)) as fetch:
    _,state,_,_=await run([decision('get_weather',variables=['temperature_c']),finish()])
    assert fetch.await_count==1 and state['tool_history'][0]['status']=='completed'
   print('PASS A: missing weather -> selected get_weather -> executed and persisted')
   # B: policy sees Critic contradiction and elects image reinspection, then verifies again.
   actions=[decision('search_diseases',query='cigar gray lesions'),decision('verify_evidence'),decision('reanalyze_image',features=['leaf underside'],differential_criteria=['Visible surface features']),decision('verify_evidence'),finish('completed')]
   _,state,_,choose=await run(actions,[critic(True),critic()])
   assert state['status']=='completed' and len(state['judge_decisions'])==2
   observed=choose.snapshots[2]
   assert observed['critic_findings']
   print('PASS B: contradiction -> policy-selected image reinspection -> re-verification -> Judge approval')
   comparison_state=state
   _,state,count,_=await run([decision('search_diseases',query='cigar gray lesions'),decision('verify_evidence'),finish('completed')],[critic()])
   assert state['status']=='completed' and count==1 and len(state['tool_history'])==3
   print('PASS C: sufficient verified evidence -> finish without unnecessary tools')
   case_id,state,_,_=await run([finish('needs_more_evidence')])
   assert state['status']=='needs_more_evidence' and state['questions']
   with TestClient(app) as client:
    assert client.get(f'/api/investigations/{case_id}').json()['status']=='needs_more_evidence'
    export=client.get(f'/api/investigations/{case_id}/agent').json()
    assert export['location']=={'confirmed':False} and 'weather' not in export
    assert client.post(f'/api/investigations/{case_id}/observations',json={'symptoms':'More details supplied'}).status_code==200
   print('PASS D: missing observations -> human question, trace export and follow-up retained')
   bad=proposal.model_copy(deep=True);bad.candidates[0].id='rice_999'
   _,state,_,_=await run([decision('search_diseases',query='cigar gray lesions'),decision('verify_evidence'),finish('completed'),finish()],generated=bad)
   assert state['status']=='abstained' and not state['disease_candidates']
   assert state['tool_history'][2]['status']=='rejected'
   print('PASS E: invented/cross-crop candidate and unverified completion rejected')
   repeated=decision('search_diseases',query='cigar gray lesions')
   _,state,count,_=await run([repeated]*5)
   assert state['status']=='abstained' and count==1
   assert sum(t['status']=='rejected' for t in state['tool_history'])==4
   print('PASS F: duplicate calls execute once; action cap abstains')
   report=compare_modes(dict(candidates=proposal.model_dump()['candidates'],steps=1,tool_calls=1,elapsed_seconds=None),comparison_state)
   assert report['diagnostic_accuracy'] is None and report['autonomous']['critic_conflicts_detected']==1
   Path('/tmp/agrisleuth-comparison-fixture.json').write_text(json.dumps(report,indent=2))
   print('PASS G: comparison exposes steps/tools/time/flags and no unlabeled accuracy claim')
   # Finish invalidation: changing a previously reviewed hypothesis must require fresh verification.
   case_id=seed();case=await database.analysis_case(case_id)
   synthetic=dict(disease_candidates=proposal.model_dump()['candidates'],judge_decisions=[{'action':'finalize'}],supporting_evidence=rows,image_observations=None,weather=None,observed_symptoms=['fixture'],status='investigating')
   synthetic['verified_fingerprint']=agent_tools.material_fingerprint(synthetic);synthetic['verified_candidates']=agent_tools.digest(synthetic['disease_candidates'])
   synthetic['disease_candidates'][0]['claim']='Changed unreviewed claim'
   try:await agent_tools.Tools(case,synthetic).finish_investigation(FinishArgs(status='completed',reason='fixture'))
   except ValueError:pass
   else:raise AssertionError('Unreviewed candidate modification accepted')
   print('PASS fresh-verification guard after hypothesis modification')
  asyncio.run(main())
 finally:admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
print('Disposable schema removed. A-G use synthetic policy/model/provider fixtures; real-service selection is tested separately.')
