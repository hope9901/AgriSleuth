"""Synthetic transport checks for strict JSON/channel handling; no model calls."""
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch
import httpx
from pydantic import BaseModel,ConfigDict
from langchain_core.messages import HumanMessage
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'critic'))
from local_model import LocalStructuredModel
class Answer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    ok:bool
OriginalClient=httpx.AsyncClient
async def run_case(message,accept,finish='stop'):
    def provider(request):
        return httpx.Response(200,json={'choices':[{'message':message,'finish_reason':finish}],'usage':{'total_tokens':7}})
    with patch('local_model.httpx.AsyncClient',lambda **kwargs:OriginalClient(transport=httpx.MockTransport(provider),**kwargs)):
        model=LocalStructuredModel('http://fixture/v1','test','fixture',Answer)
        try: result=await model.ainvoke([HumanMessage(content='fixture')])
        except ValueError:
            assert not accept
        else:
            assert accept and result.ok and model.last_usage['total_tokens']==7
async def main():
    await run_case({'content':'{"ok":true}'},True)
    await run_case({'content':'','reasoning_content':'{"ok":true}'},True)
    await run_case({'content':'','reasoning_content':'Thinking first. {"ok":true}'},False)
    await run_case({'content':'{"ok":true'},False)
    await run_case({'content':'{"ok":true,"invented":1}'},False)
    await run_case({'content':'{"ok":true}'},False,finish='length')
    await run_case({'content':''},False)
asyncio.run(main())
print('PASS strict content JSON, exact alternate-channel JSON, prose rejection, truncation rejection, extra-field rejection and finish-reason validation')

from schemas import CriticReview
from pipeline import Proposal
reviewer=LocalStructuredModel('http://fixture/v1','test','fixture',CriticReview)
reviewer.constrain_references(['maize_013'],['maize_013_f1','maize_015_f2'])
props=reviewer.output_schema()['$defs']['CriticIssue']['properties']
assert props['candidate_id']['anyOf'][0]['enum']==['maize_013']
assert props['candidate_id']['anyOf'][1]['type']=='null'
assert props['evidence_ids']['items']['enum']==['maize_013_f1','maize_015_f2']
generator=LocalStructuredModel('http://fixture/v1','test','fixture',Proposal)
generator.constrain_references(['maize_013'],['maize_013_f1'])
assert generator.output_schema()['$defs']['Candidate']['properties']['id']['enum']==['maize_013']
print('PASS request-specific candidate/source enum constraints and null alternative references')
