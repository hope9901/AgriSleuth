"""LLM policy: select one allow-listed action, never execute arbitrary instructions."""
import json
import os
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,create_model
from langchain_core.messages import HumanMessage,SystemMessage
from local_model import LocalStructuredModel
from pathlib import Path

class ToolDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool:Literal['search_diseases','get_weather','reanalyze_image','verify_evidence','finish_investigation']
    reason:str=Field(min_length=1,max_length=160)
    arguments:dict

async def select_action(state,carryover):
    allowed=['finish_investigation']
    if not state.get('search_no_progress'):allowed.append('search_diseases')
    if state['supporting_evidence'] and not state.get('verification_blocked'):allowed.append('verify_evidence')
    if state['image_reference']:allowed.append('reanalyze_image')
    if not state.get('weather_blocked'):allowed.append('get_weather')
    schema=create_model('AvailableToolDecision',__base__=ToolDecision,tool=(Literal[tuple(allowed)],...))
    model=LocalStructuredModel(os.getenv('LM_STUDIO_BASE_URL','http://localhost:1234/v1'),os.getenv('LM_STUDIO_MODEL',''),os.getenv('LM_STUDIO_API_KEY','lm-studio'),schema,max_tokens=400)
    context=dict(crop=state['crop'],observed_symptoms=[s[:900] for s in state['observed_symptoms'][:1]],
        disease_candidates=[{**c,'claim':c['claim'][:160]} for c in state['disease_candidates'][:3]],
        missing_evidence=[s[:180] for s in state['missing_evidence'][:3]],
        critic_findings=[dict(code=i['code'],severity=i['severity'],reason=i['reason'][:160],requested_information=i['requested_information'][:160]) for i in state['critic_findings'][:2]],
        judge_decisions=state['judge_decisions'][-1:],iteration=state['iteration'],max_iterations=state['max_iterations'])
    context['supporting_evidence']=[dict(id=e['id'],disease_id=e['disease_id'],name=e['name_en'],description=e['description'][:180]) for e in state['supporting_evidence'][:6]]
    context['photo_available']=bool(state['image_reference']);context['image_reference']=state['image_reference']
    image=state.get('image_observations') or {}
    context['image_observations']={k:[v[:100] for v in image.get(k,[])[:3]] for k in ('visible_findings','limitations')}
    context['weather_status']=(state.get('weather') or {}).get('status','missing')
    context['location_confirmed']=bool(state.get('location'))
    context['recent_tools']=[dict(tool=t['tool'],status=t['status'],summary=t.get('summary','')[:180],error_code=t.get('error_code')) for t in state['tool_history'][-3:]]
    context['checkpoint']=carryover[:350]
    context['available_tools']=allowed
    context['allowed_final_candidate_ids']=[c['id'] for c in state['disease_candidates']]
    context['important']='Only verify_evidence creates candidates and runs Critic/Judge. Search alone never creates hypotheses.'
    prompt=(Path(__file__).parent/'prompts/controller.md').read_text()
    result=await model.ainvoke([SystemMessage(content=prompt),HumanMessage(content=json.dumps(context,ensure_ascii=False,default=str))])
    return ToolDecision.model_validate(result)
