"""Strict JSON adapter for LM Studio, including its Qwen response-channel quirk."""
import json
import asyncio
import os
import httpx

MODEL_LOCK=asyncio.Lock()

class LocalStructuredModel:
    def __init__(self,base_url,model_name,api_key,schema,max_tokens=1500):
        self.base_url=base_url.rstrip('/');self.model_name=model_name;self.api_key=api_key;self.schema=schema;self.max_tokens=max_tokens
        self.last_usage=None
        self.reference_constraints=None
    def constrain_references(self,candidate_ids,evidence_ids):
        self.reference_constraints=(sorted(set(candidate_ids)),sorted(set(evidence_ids)))
    def output_schema(self):
        schema=self.schema.model_json_schema()
        if self.schema.__name__=='Proposal':
            schema['properties']['candidates']['maxItems']=1
            schema['properties']['summary']['maxLength']=180
            schema['properties']['limitations'].update(maxItems=2,items={'type':'string','maxLength':140})
            properties=schema['$defs']['Candidate']['properties']
            properties['claim']['maxLength']=180
            properties['evidence_ids']['maxItems']=2
        if self.schema.__name__=='CriticReview':
            schema['required']=list(dict.fromkeys(schema.get('required',[])+['scenario_id','scenario_match','scenario_reason']))
            schema['properties']['issues']['maxItems']=2
            schema['properties']['limitations'].update(maxItems=2,items={'type':'string','maxLength':140})
            schema['properties']['review_summary']['maxLength']=180
            properties=schema['$defs']['CriticIssue']['properties']
            properties['reason']['maxLength']=160
            properties['requested_information']['maxLength']=160
            properties['evidence_ids']['maxItems']=2
        if self.reference_constraints:
            candidates,evidence=self.reference_constraints
            for name,definition in schema.get('$defs',{}).items():
                properties=definition.get('properties',{})
                if name=='CriticIssue':
                    properties['candidate_id']={'anyOf':[{'type':'string','enum':candidates},{'type':'null'}]}
                    properties['evidence_ids']['items']={'type':'string','enum':evidence}
                if name=='Candidate':
                    properties['id']={'type':'string','enum':candidates}
                    properties['evidence_ids']['items']={'type':'string','enum':evidence}
        return schema
    async def ainvoke(self,messages):
        data=[]
        for msg in messages:
            role='system' if msg.type=='system' else 'user' if msg.type=='human' else 'assistant'
            data.append(dict(role=role,content=msg.content))
        payload=dict(model=self.model_name,messages=data,temperature=0.1,max_tokens=self.max_tokens,
            response_format={'type':'json_schema','json_schema':{'name':self.schema.__name__,'schema':self.output_schema(),'strict':True}},
            chat_template_kwargs={'enable_thinking':False})
        timeout=int(os.getenv('LOCAL_MODEL_TIMEOUT_SECONDS','180'))
        if not 10<=timeout<=180:raise ValueError('Local model timeout outside safe bounds.')
        async with MODEL_LOCK, httpx.AsyncClient(timeout=timeout) as client:
            response=await client.post(self.base_url+'/chat/completions',headers={'Authorization':'Bearer '+self.api_key},json=payload)
            response.raise_for_status();body=response.json()
        choice=body['choices'][0]
        if choice.get('finish_reason')!='stop':raise ValueError(f"Model response did not finish normally ({choice.get('finish_reason')}; output budget {self.max_tokens}).")
        message=choice['message'];text=message.get('content') or ''
        # Some LM Studio Qwen templates put the complete JSON answer in reasoning_content.
        # Accept ONLY an entire schema-valid JSON object there, never prose or extracted thoughts.
        if not text.strip():text=message.get('reasoning_content') or ''
        parsed=json.loads(text)
        if not isinstance(parsed,dict):raise ValueError('Expected a JSON object.')
        self.last_usage=body.get('usage')
        return self.schema.model_validate(parsed)
