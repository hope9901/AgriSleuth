"""Scenario catalog contracts with explicitly synthetic model decisions."""
import sys,json,asyncio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
from critic import call_critic_agent,CriticAgentError
from schemas import CriticReview,ReviewRequest
from pydantic import ValidationError
catalog=json.loads((ROOT/'critic/prompts/critic_scenarios.json').read_text())
assert len(catalog)==8 and len({s['id'] for s in catalog})==8
request=ReviewRequest(crop='rice',observations='No distinguishable lesions described.',candidates=[],evidence=[])
class Fake:
 async def ainvoke(self,messages):
  assert 'SOURCE_GAP' in messages[0].content and 'nearest' in messages[0].content
  return CriticReview(scenario_id='OBSERVATION_GAP',scenario_match='nearest',scenario_reason='Unlisted sensor issue most closely limits observable features.',issues=[],limitations=['No sensor measurements supplied.'],review_summary='Human observation required.')
result=asyncio.run(call_critic_agent(Fake(),request))
assert result.scenario_match=='nearest' and result.scenario_id=='OBSERVATION_GAP'
try:CriticReview(scenario_id='INVENTED_SCENARIO',issues=[],limitations=[],review_summary='Invalid')
except ValidationError:pass
else:raise AssertionError('Invented scenario accepted')
print('PASS eight-scenario catalog, runtime prompt injection, nearest rationale preservation and unknown-scenario rejection (mocked model)')
