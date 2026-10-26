"""Validated tool registry, reusing existing transport, VLM, Diagnosis, Critic and Judge."""
from config import load_environment
load_environment()
import asyncio
import hashlib
import json
import os
from datetime import date,timedelta
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from typing import Literal
import database
from retrieval import retrieve,rank_evidence
from vision import observe_photo
from weather import fetch_weather,search_locations
from critic import create_critic_reviewer,call_critic_agent
from schemas import ReviewRequest
from judge import judge_review

class Args(BaseModel):model_config=ConfigDict(extra='forbid')
class SearchArgs(Args):
    query:str=Field(min_length=3,max_length=800)
    compare_disease_ids:list[str]=Field(default_factory=list,max_length=3)
    exclude_disease_ids:list[str]=Field(default_factory=list,max_length=20)
class WeatherArgs(Args):
    latitude:float|None=Field(default=None,ge=-90,le=90)
    longitude:float|None=Field(default=None,ge=-180,le=180)
    start_date:date|None=None
    end_date:date|None=None
    variables:list[Literal['temperature_c','humidity_pct','precipitation_mm']]=Field(default_factory=lambda:['temperature_c','humidity_pct','precipitation_mm'],min_length=1,max_length=3)
    @model_validator(mode='after')
    def coordinates(self):
        if (self.latitude is None)!=(self.longitude is None):raise ValueError('Provide both coordinates or neither.')
        return self
class ImageArgs(Args):
    image_reference:str|None=None
    features:list[str]=Field(default_factory=list,max_length=8)
    differential_criteria:list[str]=Field(default_factory=list,max_length=8)
class VerifyArgs(Args):pass
class FinishArgs(Args):
    status:Literal['completed','needs_more_evidence','abstained','failed']
    reason:str=Field(min_length=1,max_length=800)
    questions:list[str]=Field(default_factory=list,max_length=5)
    uncertainties:list[str]=Field(default_factory=list,max_length=8)
    final_candidate_ids:list[str]=Field(default_factory=list,max_length=3)

SCHEMAS={'search_diseases':SearchArgs,'get_weather':WeatherArgs,'reanalyze_image':ImageArgs,'verify_evidence':VerifyArgs,'finish_investigation':FinishArgs}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()
def material_fingerprint(state):
    return digest(dict(evidence=[(e['id'],e['description']) for e in state['supporting_evidence']],image=state.get('image_observations'),weather=state.get('weather'),symptoms=state['observed_symptoms']))

def log_arguments(args):
    result=args.model_dump(mode='json')
    for key in ('latitude','longitude'):
        if result.get(key) is not None:result[key]='[confirmed coordinates redacted]'
    return result

class Tools:
    def __init__(self,case,state,progress=None):self.case=case;self.state=state;self.rows=None;self.progress=progress
    async def notify(self,phase,summary):
        self.state['phase']=phase
        if self.progress:await self.progress(phase,summary)
    async def search_diseases(self,args):
        if self.rows is None:self.rows=await retrieve(self.case['crop'])
        if any(not r['disease_id'].startswith(self.case['crop']+'_') for r in self.rows):raise ValueError('Source disease IDs do not match the case crop.')
        known={r['disease_id'] for r in self.rows}
        if (set(args.compare_disease_ids)|set(args.exclude_disease_ids))-known:raise ValueError('Search disease IDs must belong to the case crop and source database.')
        rows=[r for r in self.rows if r['disease_id'] not in args.exclude_disease_ids and (not args.compare_disease_ids or r['disease_id'] in args.compare_disease_ids)]
        selected=rank_evidence(rows,args.query)
        merged={e['id']:e for e in self.state['supporting_evidence']}
        added=[e['id'] for e in selected if e['id'] not in merged]
        # Keep a bounded pool; preserve the newest evidence and then prior context.
        merged.update({e['id']:e for e in selected})
        ordered=selected+[e for e in merged.values() if e['id'] not in {r['id'] for r in selected}]
        self.state['supporting_evidence']=ordered[:8]
        retained={e['id'] for e in self.state['supporting_evidence']}
        self.state['disease_candidates']=[c for c in self.state['disease_candidates'] if set(c['evidence_ids'])<=retained]
        return dict(source='Zetaris',new_source_ids=added,source_ids=[e['id'] for e in selected],disease_names={e['disease_id']:e['name_en'] for e in selected},disease_ids=sorted({e['disease_id'] for e in selected}),summary=f'Zetaris evidence: {len(selected)} excerpts, {len(added)} new source IDs.')
    async def get_weather(self,args):
        if not self.case.get('observed_date'):
            raise ValueError('An observation date is needed for historical weather; do not assume today.')
        end=args.end_date or self.case['observed_date'];start=args.start_date or end
        if start>end or end>self.case['observed_date'] or (end-start).days>2:raise ValueError('Weather period must cover 1–3 days on/before the observation date.')
        place=self.state.get('location')
        if not place:
            candidates=await search_locations(self.case['region'])
            if len(candidates)!=1:
                return dict(status='needs_location_confirmation',summary='The region is ambiguous or not found. Confirm a location in the weather panel.',missing=['Confirmed location'])
            place=candidates[0];self.state['location']=place
        if args.latitude is not None and (abs(args.latitude-place['latitude'])>0.01 or abs(args.longitude-place['longitude'])>0.01):
            raise ValueError('Weather coordinates must match the confirmed growing location.')
        cache=self.state.get('weather')
        period=[start.isoformat(),end.isoformat()]
        if cache and cache.get('observations') and (cache.get('agent_period')==period or (start==end and cache.get('observed_date')==end.isoformat())):
            from environment import attach_environment
            cache['case_observed_date']=self.case['observed_date'].isoformat()
            await attach_environment(cache,self.case['crop'])
            await database.save_weather(UUID(self.state['investigation_id']),place['id'],cache)
            return dict(status='cached',summary='Existing weather snapshot reused; no external request made.')
        days=[];day=start
        while day<=end:
            report=await asyncio.wait_for(fetch_weather(place['id'],day),timeout=45)
            days.append(report)
            if not report.get('observations'):break
            day+=timedelta(days=1)
        report=days[-1]
        report['agent_period']=period;report['daily_reports']=days[:-1]
        report['case_observed_date']=self.case['observed_date'].isoformat()
        report['region_entered']=self.case['region']
        # Preserve the existing weather UI shape; multi-day detail is retained separately.
        from environment import attach_environment
        await attach_environment(report,self.case['crop'])
        report.setdefault('comparisons',[])
        self.state['weather']=report
        await database.save_weather(UUID(self.state['investigation_id']),place['id'],report)
        missing=list(dict.fromkeys(report.get('limitations',[])))
        return dict(status=report['status'],summary=f"KMA returned {sum(len(d.get('observations',[])) for d in days)} observations across {len(days)} requested day results.",period=period,requested_variables=args.variables,missing=missing)
    async def reanalyze_image(self,args):
        reference=self.state['image_reference']
        if not reference:raise ValueError('No existing photograph is available.')
        if args.image_reference and args.image_reference!=reference:raise ValueError('Image reference must match this investigation.')
        requests=' '.join(args.features+args.differential_criteria).lower()
        if any(r['name_en'].lower() in requests or r['disease_id'].lower() in requests for r in (self.rows or [])):
            raise ValueError('Image inspection must ask about visible morphology, not a target disease.')
        photo=await database.get_photo(UUID(reference))
        if not photo:raise ValueError('The stored photograph is unavailable.')
        findings=await observe_photo(photo,features=args.features,differential_criteria=args.differential_criteria)
        data=findings.model_dump();self.state['image_observations']=data;self.case['image_observations']=data
        return dict(summary='Tentative image observations updated; invisible features remain unknown.',observations=data)
    async def verify_evidence(self,args):
        from pipeline import generate,validate_proposal
        evidence=self.state['supporting_evidence']
        if not evidence:raise ValueError('Retrieve source evidence before verification.')
        self.state.pop('verified_fingerprint',None)
        self.state.pop('verified_candidates',None)
        feedback=self.state.get('last_review')
        self.case['weather_context']={k:(self.state.get('weather') or {}).get(k) for k in ('status','observed_date','summary','limitations','environment_assessments')}
        weather_context=self.case['weather_context']
        weather_context['environment_assessments']=[dict(disease_id=a['disease_id'],assessment=a['assessment'],required_inputs=a['required_inputs'],checks=[{k:c[k] for k in ('metric','samples_matching','valid_samples')} for c in a['checks']],windows=[{k:w.get(k) for k in ('window_id','coverage','covered_days','required_days')} for w in a['windows'] if w['core']][:2]) for a in weather_context.get('environment_assessments') or [] if a['disease_id'] in {e['disease_id'] for e in evidence}][:2]
        weather_context['environment_assessments']=weather_context['environment_assessments'][:1]
        weather_context['limitations']=[text[:130] for text in (weather_context.get('limitations') or [])[:2]]
        await self.notify('diagnosis','Generating source-linked hypotheses from the current evidence.')
        proposal=await generate(self.case,evidence,self.state.get('carryover',''),feedback)
        validate_proposal(proposal,evidence)
        self.state['disease_candidates']=[c.model_dump() for c in proposal.candidates]
        self.state['proposal_summary']=proposal.summary;self.state['proposal_limitations']=proposal.limitations
        if not proposal.candidates:
            self.state['judge_decisions'].append(dict(action='abstain',reason='No source-supported candidate was generated.'))
            return dict(summary='Diagnosis generated no supported candidate.',action='abstain')
        reviewer=create_critic_reviewer(base_url=os.getenv('LM_STUDIO_BASE_URL','http://localhost:1234/v1'),model_name=os.getenv('LM_STUDIO_MODEL',''),api_key=os.getenv('LM_STUDIO_API_KEY','lm-studio'))
        observations='Already supplied case context: '+json.dumps({k:str(self.case.get(k) or 'unknown') for k in ('crop','region','observed_date','growth_stage','affected_part')})+'\nObserved symptoms: '+self.case['symptoms']
        if self.state.get('image_observations'):observations+='\nUnconfirmed AI image observations: '+json.dumps(self.state['image_observations'])[:1500]
        request=ReviewRequest(crop=self.case['crop'],observations=observations[:5000],candidates=proposal.candidates,evidence=[dict(id=e['id'],disease_id=e['disease_id'],disease_name=e['name_en'],text=e['description'][:4000],source=e['source_name'],location=e.get('source_location') or 'Unspecified') for e in evidence],weather_summary=json.dumps(self.case['weather_context'],default=str)[:2000],review_round=min(len(self.state['judge_decisions'])+1,3))
        await self.notify('critic','Critic is checking hypothesis claims, sources and unresolved observations.')
        review=await call_critic_agent(reviewer,request)
        await self.notify('judge','Deterministic Judge is evaluating the current Critic findings.')
        action,reason=judge_review(review,len(self.state['judge_decisions'])+1,max_rounds=self.state['max_iterations'])
        self.state['last_review']=review.model_dump()
        self.state['critic_findings']=[i.model_dump() for i in review.issues]
        self.state['missing_evidence']=list(dict.fromkeys(i.requested_information for i in review.issues if i.severity=='blocking'))
        self.state['contradicting_evidence']=[dict(source_ids=i.evidence_ids,reason=i.reason) for i in review.issues if i.code=='OBSERVATION_MISMATCH']
        self.state['judge_decisions'].append(dict(action=action,reason=reason))
        self.state['verified_fingerprint']=material_fingerprint(self.state)
        self.state['verified_candidates']=digest(self.state['disease_candidates'])
        record=dict(round=len(self.state['judge_decisions']),proposal=proposal.model_dump(),review=review.model_dump(),action=action,reason=reason,evidence_ids=[e['id'] for e in evidence])
        await database.save_round(UUID(self.state['investigation_id']),record)
        self.state['hypothesis_history'].append(record)
        return dict(summary=review.review_summary,action=action,reason=reason,missing=self.state['missing_evidence'],candidate_ids=[c.id for c in proposal.candidates])
    async def finish_investigation(self,args):
        candidates=self.state['disease_candidates'];known={c['id'] for c in candidates}
        invalid_ids=set(args.final_candidate_ids)-known
        if invalid_ids and args.status=='completed':raise ValueError('Final candidates must be existing source-linked hypotheses.')
        if invalid_ids:self.state['excluded_unverified_final_ids']=sorted(invalid_ids)
        if args.status=='completed':
            latest=self.state['judge_decisions'][-1] if self.state['judge_decisions'] else {}
            if not candidates or latest.get('action') not in ('finalize','finalize_with_limitations') or self.state.get('verified_fingerprint')!=material_fingerprint(self.state) or self.state.get('verified_candidates')!=digest(candidates):
                raise ValueError('Cannot complete without current source-supported hypotheses and a passing Critic/Judge verification.')
        if args.status=='needs_more_evidence' and not any(q.strip() for q in args.questions):raise ValueError('Request a specific missing observation.')
        self.state.update(status=args.status,finish_reason=args.reason,questions=args.questions,uncertainties=args.uncertainties)
        if args.final_candidate_ids:self.state['disease_candidates']=[c for c in candidates if c['id'] in args.final_candidate_ids and c['id'] in known]
        return dict(status=args.status,summary=args.reason)
