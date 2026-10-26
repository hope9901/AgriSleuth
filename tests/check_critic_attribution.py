"""Structural citation attribution checks, synthetic reviewer, no provider calls."""
import sys,asyncio
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'critic'))
from critic import call_critic_agent,CriticAgentError
from schemas import ReviewRequest,CriticReview,CriticIssue
request=ReviewRequest(crop='maize',observations='Synthetic symptoms',candidates=[dict(id='maize_013',name='NCLB',claim='Tentative',evidence_ids=['e1'])],evidence=[dict(id='e1',disease_id='maize_013',disease_name='NCLB',text='Fixture A',source='Fixture',location='Test'),dict(id='e2',disease_id='maize_015',disease_name='GLS',text='Fixture B',source='Fixture',location='Test')])
class Reviewer:
    def __init__(self,candidate_id,evidence_id,code):self.candidate_id=candidate_id;self.evidence_id=evidence_id;self.code=code
    async def ainvoke(self,messages):
        return CriticReview(issues=[CriticIssue(code=self.code,severity='advisory',candidate_id=self.candidate_id,reason='Synthetic finding',evidence_ids=[self.evidence_id],suggested_action='revise_conclusion',requested_information='Synthetic request')],limitations=[],review_summary='Synthetic review')
async def main():
    try:await call_critic_agent(Reviewer('maize_013','e2','OBSERVATION_MISMATCH'),request)
    except CriticAgentError:pass
    else:raise AssertionError('Other-disease mismatch reference accepted')
    assert await call_critic_agent(Reviewer('maize_013','e1','OBSERVATION_MISMATCH'),request)
    assert await call_critic_agent(Reviewer(None,'e2','MISSING_DIFFERENTIAL'),request)
asyncio.run(main())
print('PASS candidate mismatch must cite its own disease; case-wide alternative evidence remains allowed')
