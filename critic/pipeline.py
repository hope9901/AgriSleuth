"""Durable investigation loop; Meterless runtime controls bounded chunks."""
import asyncio
import json
import os
import shutil
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
from pydantic import BaseModel,Field,ConfigDict
from langchain_core.messages import HumanMessage,SystemMessage
from schemas import Candidate,ReviewRequest
from critic import call_critic_agent,create_critic_reviewer
from judge import judge_review
from retrieval import retrieve,rank_evidence,RetrievalError
import database

ROOT=Path(__file__).resolve().parents[1]
class Proposal(BaseModel):
    model_config=ConfigDict(extra="forbid")
    candidates:list[Candidate]=Field(max_length=3)
    summary:str
    limitations:list[str]

def strip_control_markers(text):
    for marker in ('[TASK_COMPLETE]','[STATE_CHECKPOINT]','@@@STATE@@@','[STATE]','---STATE---','@@@FINAL@@@','[FINAL]','---FINAL---'):
        text=text.replace(marker,'')
    return text

def event(node,summary):
    return dict(id=str(uuid4()),timestamp=datetime.now(timezone.utc).isoformat(),node=node,summary=summary)

def validate_proposal(proposal, evidence):
    known={e['id']:e for e in evidence}
    if len({c.id for c in proposal.candidates})!=len(proposal.candidates):raise ValueError('Duplicate candidate IDs.')
    for c in proposal.candidates:
        if not c.evidence_ids or any(i not in known or known[i]['disease_id']!=c.id for i in c.evidence_ids):
            raise ValueError('Candidate evidence provenance is invalid.')
        if c.name!=next(known[i]['name_en'] for i in c.evidence_ids):raise ValueError('Candidate name does not match disease ID.')

async def generate(case,evidence,carryover,feedback):
    model_name=os.getenv('LM_STUDIO_MODEL','').strip()
    if not model_name:raise RuntimeError('Configure and load LM_STUDIO_MODEL before running investigation.')
    from local_model import LocalStructuredModel
    model=LocalStructuredModel(os.getenv('LM_STUDIO_BASE_URL','http://localhost:1234/v1'),model_name,os.getenv('LM_STUDIO_API_KEY','lm-studio'),Proposal,max_tokens=350)
    model.constrain_references([e['disease_id'] for e in evidence],[e['id'] for e in evidence])
    prompt=(ROOT/'critic/prompts/hypothesis.md').read_text()
    # Bounded evidence and carryover, never the entire prior conversation.
    payload=dict(observations={k:str(case.get(k) or '') for k in ('crop','region','observed_date','growth_stage','affected_part','symptoms')},image_observations=case.get('image_observations'),weather_context=case.get('weather_context'),evidence=[{k:e.get(k) for k in ('id','disease_id','name_en','description','source_name','source_location','source_conflicts')} for e in evidence],carryover=carryover[:2048],previous_review=feedback)
    proposal=await model.ainvoke([SystemMessage(content=prompt),HumanMessage(content=json.dumps(payload,ensure_ascii=False))])
    proposal=Proposal.model_validate(proposal);validate_proposal(proposal,evidence)
    return proposal

async def execute_fixed(case_id):
    process=None
    try:
        async with asyncio.timeout(540):
            case=await database.analysis_case(case_id)
            result=case['result'];result['status']='researching'
            result['events'].append(event('retrieve','Searching disease evidence through Zetaris.'))
            await database.update_analysis(case_id,result)
            image_limitation='Image interpretation was not used.'
            if os.getenv('USE_IMAGE_OBSERVATIONS','true').lower()=='true' and result.get('photoId'):
                result['events'].append(event('observe_image','Extracting tentative visual observations with the local vision model.'))
                await database.update_analysis(case_id,result)
                try:
                    from vision import observe_photo
                    from uuid import UUID
                    photo=await database.get_photo(UUID(result['photoId']))
                    findings=await observe_photo(photo)
                    case['image_observations']=findings.model_dump()
                    result['events'].append(event('observe_image','AI visual observations (unconfirmed): '+'; '.join(findings.visible_findings)))
                    image_limitation='Image observations are AI-generated and require researcher confirmation. '+'; '.join(findings.limitations)
                except Exception:
                    image_limitation='Image interpretation was unavailable; analysis uses researcher-entered symptoms.'
                    result['events'].append(event('observe_image',image_limitation))
            rows=await retrieve(case['crop'])
            selected=rank_evidence(rows,case['symptoms']+' '+case['affected_part'])
            if not selected:
                result.update(status='abstained',summary='No sufficiently matching symptom evidence was retrieved.',nextAction='Describe lesion shape, color and affected plant part in more detail.',limitations=['No diagnosis was generated.'])
                await database.update_analysis(case_id,result);return
            node=os.getenv('NODE_BINARY') or shutil.which('node')
            if not node:raise RuntimeError('Node.js with TypeScript transform support is required for Meterless.')
            process=await asyncio.create_subprocess_exec(node,'--experimental-transform-types',str(ROOT/'engines/meterless-markovian/bridge.mjs'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=1024*1024)
            async def send(data):
                process.stdin.write((json.dumps(data)+'\n').encode());await process.stdin.drain()
            await send(dict(goal='Investigate crop symptom hypotheses with cited evidence and resolve material Critic findings.'))
            previous=None;rounds=[];action='abstain'
            reviewer=create_critic_reviewer(base_url=os.getenv('LM_STUDIO_BASE_URL','http://localhost:1234/v1'),model_name=os.getenv('LM_STUDIO_MODEL',''),api_key=os.getenv('LM_STUDIO_API_KEY','lm-studio'))
            weather=await database.read_weather(case_id)
            weather_summary='Weather evidence is unavailable.'
            if weather:
                weather_summary=json.dumps({k:weather.get(k) for k in ('status','location','region_entered','observed_date','station','summary','limitations')},ensure_ascii=False)[:2000]
            while True:
                line=await process.stdout.readline()
                if not line:raise RuntimeError('Meterless engine ended without a run record.')
                message=json.loads(line)
                if message['type']=='done':
                    engine=message['run'];engine['id']=str(uuid4())
                    await database.save_engine(case_id,engine,rounds)
                    if engine['status']=='errored':raise RuntimeError('Meterless engine reported an execution error.')
                    if action not in ('finalize','finalize_with_limitations','request_user_input','abstain'):
                        action='abstain';result['nextAction']='The engine stopped before validation completed. Researcher review is required.'
                    break
                step=message['step']
                result['events'].append(event('hypothesize',f'Round {step}: generating source-linked hypotheses.'))
                result['status']='researching';await database.update_analysis(case_id,result)
                proposal=await generate(case,selected,message['carryover'],previous)
                result['hypotheses']=[dict(id=c.id,name=c.name,reasoning=c.claim,evidenceIds=c.evidence_ids) for c in proposal.candidates]
                result['evidence']=[dict(id=e['id'],title=e['source_name'],excerpt=e['description'],url=e['urls'][0],location=e['source_location']) for e in selected]
                result['summary']=proposal.summary
                result['limitations']=list(dict.fromkeys(proposal.limitations+['Research hypotheses, not confirmed diagnoses.',image_limitation]))
                if not proposal.candidates:
                    action='abstain';review=None;reason='The model could not support a candidate with the supplied evidence.'
                else:
                    result['status']='reviewing';result['events'].append(event('critic',f'Round {step}: checking claims and citation provenance.'));await database.update_analysis(case_id,result)
                    request=ReviewRequest(crop=case['crop'],observations=case['symptoms'],candidates=proposal.candidates,evidence=[dict(id=e['id'],disease_id=e['disease_id'],disease_name=e['name_en'],text=e['description'][:4000],source=e['source_name'],location=e['source_location'] or 'Unspecified') for e in selected],weather_summary=weather_summary,review_round=step)
                    review=await call_critic_agent(reviewer,request)
                    action,reason=judge_review(review,step)
                result['reviewIssues']=[dict(id=f'r{step}_{i}',severity=issue.severity,reason=issue.reason) for i,issue in enumerate(review.issues)] if review else []
                result['events'].append(event('judge',f'Round {step}: {action}. {reason}'))
                record=dict(round=step,proposal=proposal.model_dump(),review=review.model_dump() if review else None,action=action,reason=reason,evidence_ids=[e['id'] for e in selected])
                previous=review.model_dump() if review else None
                if action=='request_user_input':
                    result['questions']=list(dict.fromkeys(i.requested_information for i in review.issues if i.suggested_action=='request_user_input'))
                result['nextAction']=reason
                done=action in ('finalize','finalize_with_limitations','request_user_input','abstain')
                if action=='retrieve_evidence':
                    query=case['symptoms']+' '+' '.join(i.requested_information for i in review.issues)
                    rows=await retrieve(case['crop'])
                    additional=rank_evidence(rows,query,excluded={e['id'] for e in selected})
                    if additional:
                        selected=(selected[:3]+additional[:3])[:6]
                        result['events'].append(event('retrieve','Retrieved additional Zetaris source excerpts for the next round.'))
                    else:
                        action='abstain';done=True;result['nextAction']='No additional supporting evidence was found. Researcher review is required.'
                record['action']=action;record['reason']=result['nextAction']
                rounds.append(record);await database.save_round(case_id,record)
                if not weather or weather.get('status')=='unavailable':
                    if 'KMA weather observations were unavailable for this run.' not in result['limitations']:
                        result['limitations'].append('KMA weather observations were unavailable for this run.')
                checkpoint='COMPLETED: reviewed round '+str(step)+'\nREMAINING: '+('none' if done else action)+'\nDECISIONS: '+action+'\nCONTEXT: '+json.dumps(previous or {},ensure_ascii=False)[:1200]
                checkpoint=strip_control_markers(checkpoint)
                content=strip_control_markers(json.dumps(dict(summary=proposal.summary,action=action),ensure_ascii=False))
                content+='\n[TASK_COMPLETE]' if done else '\n[STATE_CHECKPOINT]\n'+checkpoint
                await database.update_analysis(case_id,result)
                await send(dict(content=content))
            result['status']='needs_input' if action=='request_user_input' else 'abstained' if action=='abstain' else 'completed'
            result['events'].append(event('report',f'Investigation ended: {result["status"]}.'))
            await database.update_analysis(case_id,result)
    except asyncio.CancelledError:
        await database.fail_analysis(case_id,'Investigation interrupted. Restart it after checking services.');raise
    except TimeoutError:
        await database.fail_analysis(case_id,'The nine-minute investigation budget was reached. Partial evidence and rounds were retained.')
    except Exception as exc:
        # Do not expose provider URLs, tokens, database traces or untrusted raw errors.
        detail=str(exc) if isinstance(exc,(RetrievalError,RuntimeError)) else 'Investigation failed during model execution or validation. Check local services and retry.'
        await database.fail_analysis(case_id,detail[:300])
    finally:
        if process and process.returncode is None:
            process.kill();await process.wait()


async def execute(case_id):
    from agent_runtime import execute as autonomous_execute
    await autonomous_execute(case_id)
