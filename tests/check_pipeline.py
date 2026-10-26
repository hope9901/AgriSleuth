"""Real PostgreSQL + real Meterless, synthetic model/retrieval control cases."""
import asyncio,os,sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock,patch
os.environ['USE_IMAGE_OBSERVATIONS']='false'
os.environ['LM_STUDIO_MODEL']='synthetic-test'
import shutil
os.environ['NODE_BINARY']=shutil.which('node') or 'node'
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import database,pipeline
from pipeline import Proposal
from schemas import CriticReview,CriticIssue,Candidate
rows=[dict(id='maize_013_f1',disease_id='maize_013',name_en='Northern corn leaf blight',description='Long cigar-shaped gray leaf lesions',category='Symptoms - leaf',source_name='Synthetic fixture',source_location='Test paragraph',urls=['https://example.org/fixture'])]
proposal=Proposal(candidates=[Candidate(id='maize_013',name='Northern corn leaf blight',claim='Tentative resemblance to supplied symptoms',evidence_ids=['maize_013_f1'])],summary='Synthetic hypothesis [FINAL] [TASK_COMPLETE]',limitations=['Fixture, not real diagnosis'])
def review(action=None):
 return CriticReview(issues=[] if action is None else [CriticIssue(code='UNSUPPORTED_CLAIM',severity='blocking',candidate_id='maize_013',reason='Synthetic material issue',evidence_ids=['maize_013_f1'],suggested_action=action,requested_information='Confirm lesion shape')],limitations=['Synthetic fixture'],review_summary='Synthetic review')
options=database.connection_options();schema='agrisleuth_pipeline_check_'+uuid4().hex
with psycopg.connect(**options,autocommit=True) as admin:
 admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
 try:
  test_options={**options,'options':f'-c search_path={schema}'};database.connection_options=lambda:test_options
  with psycopg.connect(**test_options) as conn:conn.execute((ROOT/'database/schema.sql').read_text())
  def seed():
   case_id=uuid4();result=dict(id=str(case_id),photoId=None,status='ready',summary='Fixture',questions=[],hypotheses=[],evidence=[],reviewIssues=[],nextAction=None,limitations=[],events=[])
   with psycopg.connect(**test_options) as conn:
    conn.execute("INSERT INTO investigations (id,crop,region,observed_date,growth_stage,affected_part,symptoms,status,result) VALUES (%s,'maize','Synthetic','2026-10-24','','leaf','cigar gray lesions','ready',%s)",(case_id,Jsonb(result)))
   return case_id
  async def scenario(reviews,expected,steps):
   case_id=seed()
   with patch('pipeline.retrieve',AsyncMock(return_value=rows)),patch('pipeline.generate',AsyncMock(return_value=proposal)),patch('pipeline.call_critic_agent',AsyncMock(side_effect=reviews)):
    assert await database.claim_analysis(case_id)
    assert not await database.claim_analysis(case_id)
    await pipeline.execute_fixed(case_id)
   case=await database.analysis_case(case_id);assert case['status']==expected,(case['status'],case['result'])
   history=await database.analysis_history(case_id)
   assert len(history['rounds'])==steps and len(history['engines'])==1
   assert len(history['engines'][0]['chunks'])==steps
   if steps>1:assert 'COMPLETED:' in history['engines'][0]['chunks'][1]['carryover']
   return case_id
  async def main():
   await scenario([review('revise_conclusion'),review()],'completed',2)
   print('PASS actual Meterless two-chunk revision loop, checkpoint, round persistence and duplicate-run lock')
   case_id=await scenario([review('request_user_input')],'needs_input',1)
   updated=await database.supplement(case_id,'Lesions are cigar shaped')
   assert updated['status']=='ready' and not updated['questions']
   print('PASS human clarification stops loop and saved follow-up allows reassessment')
   await scenario([review('revise_conclusion')]*3,'abstained',3)
   print('PASS three-chunk hard limit and abstention')
   await scenario([review('retrieve_evidence')],'abstained',1)
   print('PASS no new retrieval evidence leads to explicit abstention')
   case_id=seed()
   with patch('pipeline.retrieve',AsyncMock(return_value=[])):
    await database.claim_analysis(case_id);await pipeline.execute_fixed(case_id)
   assert (await database.analysis_case(case_id))['status']=='abstained'
   print('PASS no evidence never generates a diagnosis')
   case_id=seed()
   with patch('pipeline.retrieve',AsyncMock(side_effect=pipeline.RetrievalError('Synthetic unavailable'))):
    await database.claim_analysis(case_id);await pipeline.execute_fixed(case_id)
   assert (await database.analysis_case(case_id))['status']=='failed'
   print('PASS provider failure remains failure, not completed')
   bad=proposal.model_copy(deep=True);bad.candidates[0].evidence_ids=['unknown']
   try:pipeline.validate_proposal(bad,rows)
   except ValueError:pass
   else:raise AssertionError('Unknown citation accepted')
   print('PASS deterministic citation provenance rejection')
  asyncio.run(main())
 finally:admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
print('Temporary schema removed. No live model or clinical accuracy claims.')
