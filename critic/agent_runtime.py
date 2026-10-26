"""Observe/reason/select/execute/evaluate/replan, bounded by Meterless and host guards."""
from config import load_environment
load_environment()
import asyncio,json,os,shutil,time
from pathlib import Path
from uuid import UUID,uuid4
from pydantic import ValidationError
import database
from agent_controller import select_action,ToolDecision
from agent_tools import Tools,SCHEMAS,digest,material_fingerprint,log_arguments
from pipeline import event,strip_control_markers
ROOT=Path(__file__).resolve().parents[1]


def configuration():
    steps=int(os.getenv('AGENT_MAX_ITERATIONS','5'));seconds=int(os.getenv('AGENT_DEADLINE_SECONDS','480'))
    if not 1<=steps<=10 or not 30<=seconds<=600:raise ValueError('Agent configuration outside safe bounds.')
    return steps,seconds


def result_from_state(case,state,result):
    result['status']=state['status'] if state['status']!='investigating' else ('reviewing' if state.get('phase')=='critic' else 'researching')
    result['summary']=state.get('proposal_summary') or state.get('finish_reason') or 'Agent is investigating the available evidence.'
    result['hypotheses']=[dict(id=c['id'],name=c['name'],reasoning=c['claim'],evidenceIds=c['evidence_ids']) for c in state['disease_candidates']]
    result['evidence']=[dict(id=e['id'],title=e['source_name'],excerpt=e['description'],url=e['urls'][0],location=e.get('source_location')) for e in state['supporting_evidence']]
    result['reviewIssues']=[dict(id=f'issue_{i}',severity=f['severity'],reason=f['reason']) for i,f in enumerate(state['critic_findings'])]
    result['questions']=state.get('questions',[])
    result['nextAction']=state.get('finish_reason') or (state['judge_decisions'][-1]['reason'] if state['judge_decisions'] else 'Agent selects the next investigation action.')
    result['limitations']=list(dict.fromkeys(state.get('proposal_limitations',[])+state.get('uncertainties',[])+['Tentative research hypotheses, not confirmed diagnoses.','No verified pesticide or regulatory recommendation is implemented.']+([] if (state.get('weather') or {}).get('observations') else ['KMA observations were unavailable or not requested.'])+(['Image findings are unconfirmed model observations.'] if state.get('image_observations') else ['Image interpretation was not used.'])))
    return result

async def execute(case_id):
    process=None;state=None;run_id=uuid4();started=time.monotonic()
    try:
        steps,seconds=configuration()
        case=await database.analysis_case(case_id);result=case['result'];saved=await database.read_weather(case_id)
        location=await database.read_agent_location(case_id) or (saved or {}).get('location')
        state=dict(investigation_id=str(case_id),crop=case['crop'],location=location,observed_symptoms=[case['symptoms']],image_reference=result.get('photoId'),image_observations=None,disease_candidates=[],supporting_evidence=[],contradicting_evidence=[],missing_evidence=[],tool_history=[],critic_findings=[],judge_decisions=[],hypothesis_history=[],iteration=0,max_iterations=steps,status='investigating',next_action=None,weather=saved,carryover='',questions=[],uncertainties=[],run_id=str(run_id),budget_seconds=seconds,elapsed_seconds=0)
        state['weather_context_available']=bool(case['observed_date'] and (case['region'] or location))
        result['events'].append(event('agent_initialize','Agent Controller will choose tools from the allowed registry.'))
        async def persist():
            state['elapsed_seconds']=round(time.monotonic()-started,2)
            await database.save_agent_state(run_id,case_id,state)
            await database.update_analysis(case_id,result_from_state(case,state,result))
        await persist()
        async def progress(phase,summary):
            result['events'].append(event(phase,summary));await persist()
        tools=Tools(case,state,progress=progress);signatures=set();weather_failed=False;no_progress_searches=0
        node=os.getenv('NODE_BINARY') or shutil.which('node')
        if not node:raise RuntimeError('Node with TypeScript transform support is required for Meterless.')
        process=await asyncio.create_subprocess_exec(node,'--experimental-transform-types',str(ROOT/'engines/meterless-markovian/bridge.mjs'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=1024*1024)
        async def send(data):
            process.stdin.write((json.dumps(data)+'\n').encode());await process.stdin.drain()
        await send(dict(goal='Choose and execute evidence tools to resolve crop hypothesis uncertainty; finish only after verification or abstain.',maxChunks=steps))
        async with asyncio.timeout(max(0.01,seconds-(time.monotonic()-started))):
            while True:
                line=await process.stdout.readline()
                if not line:raise RuntimeError('Meterless runtime ended without a run record.')
                message=json.loads(line)
                if message['type']=='done':
                    engine=message['run'];engine['id']=str(uuid4());await database.save_engine(case_id,engine,[])
                    if engine['status']=='errored':raise RuntimeError('Meterless runtime reported an error.')
                    break
                state['iteration']=message['step'];state['carryover']=message.get('carryover','')[:2048];state['phase']='select_tool'
                result['events'].append(event('agent_reason',f"Action {state['iteration']}/{steps}: selecting the next tool."));await persist()
                try:
                    decision=ToolDecision.model_validate(await select_action(state,state['carryover']))
                except (ValidationError,ValueError):
                    entry=dict(step=state['iteration'],tool='invalid_selection',reason='Model output did not match the allowed decision schema.',arguments={},status='rejected',summary='No tool executed; select a valid action.')
                    state['tool_history'].append(entry);state['missing_evidence']=['The previous selection was invalid; choose an allowed tool and valid arguments.']
                else:
                    entry=dict(step=state['iteration'],tool=decision.tool,reason=decision.reason,arguments={},status='validating',summary='')
                    state['tool_history'].append(entry);state['next_action']=decision.tool
                    try:
                        args=SCHEMAS[decision.tool].model_validate(decision.arguments)
                        entry['arguments']=log_arguments(args)
                        canonical=args.model_dump(mode='json')
                        for key,value in list(canonical.items()):
                            if isinstance(value,str):canonical[key]=' '.join(value.lower().split())
                            elif isinstance(value,list):canonical[key]=sorted(set(value))
                        signature=digest([decision.tool,canonical])
                        if decision.tool=='finish_investigation':signature=digest([signature,state.get('verified_fingerprint'),digest(state['disease_candidates'])])
                        if decision.tool=='verify_evidence':signature=digest([signature,material_fingerprint(state),state.get('last_review')])
                        if signature in signatures:raise ValueError('Duplicate tool and arguments rejected; no tool executed.')
                        if decision.tool=='verify_evidence' and state.get('verification_blocked'):raise ValueError('Verification failed or unchanged. Gather materially new evidence or finish with limitations.')
                        if decision.tool=='search_diseases' and no_progress_searches>=1:raise ValueError('Repeated searches added no new evidence. Address another uncertainty or finish.')
                        if decision.tool=='get_weather' and weather_failed:raise ValueError('Weather already failed or needs location confirmation; do not retry in this run.')
                        signatures.add(signature);entry['status']='running'
                        result['events'].append(event('agent_tool',f'{decision.tool}: {decision.reason}'));await persist()
                        output=await getattr(tools,decision.tool)(args)
                        entry.update(status='completed',summary=output.get('summary','Tool returned.'),result=output)
                        if decision.tool=='search_diseases':no_progress_searches=0 if output.get('new_source_ids') else no_progress_searches+1
                        elif decision.tool in ('verify_evidence','reanalyze_image'):no_progress_searches=0
                        state['search_no_progress']=no_progress_searches
                        if (decision.tool=='search_diseases' and output.get('new_source_ids')) or decision.tool in ('reanalyze_image','get_weather'):
                            state['verification_blocked']=False
                        if decision.tool=='search_diseases' and not output.get('new_source_ids'):
                            state['missing_evidence']=['The search added no new sources. Existing excerpts can be verified; candidates are created only by verify_evidence.']
                        if decision.tool=='get_weather' and output.get('status') in ('unavailable','needs_location_confirmation'):weather_failed=True;state['weather_blocked']=True
                        result['events'].append(event(decision.tool,entry['summary']))
                    except (ValidationError,ValueError) as exc:
                        # Validation errors are summarized without echoing raw user arguments or values.
                        entry.update(status='rejected',summary=('Invalid argument fields: '+', '.join(str(error['loc'][0]) if error['loc'] and str(error['loc'][0]) in SCHEMAS[decision.tool].model_fields else 'unexpected field' for error in exc.errors()))[:300] if isinstance(exc,ValidationError) else str(exc)[:300])
                    except Exception as exc:
                        entry['error_code']=type(exc).__name__
                        if decision.tool=='verify_evidence':state['verification_blocked']=True
                        entry.update(status='failed',summary='Tool provider failed; no successful evidence was fabricated.')
                        if decision.tool=='get_weather':weather_failed=True;state['weather_blocked']=True
                    if entry['status'] in ('failed','rejected'):state['missing_evidence']=[entry['summary']]
                state['phase']='tool_complete'
                done=state['status']!='investigating'
                if not done and state['iteration']>=steps:
                    state.update(status='abstained',finish_reason='The configured action budget was reached before a verified report was finalized.')
                    done=True
                await persist()
                checkpoint='COMPLETED: '+entry['tool']+' '+entry['status']+'\nREMAINING: '+('; '.join(state['missing_evidence'])[:500] or 'Choose next action or finish')+'\nDECISIONS: '+state['status']+'\nCONTEXT: '+entry['summary'][:400]
                content=strip_control_markers(json.dumps(dict(tool=entry['tool'],reason=entry.get('reason'),status=entry['status'],summary=entry['summary']),ensure_ascii=False))
                content+='\n[TASK_COMPLETE]' if done else '\n[STATE_CHECKPOINT]\n'+strip_control_markers(checkpoint)
                await send(dict(content=content))
        if state['status']=='investigating':state.update(status='abstained',finish_reason='The runtime stopped before a verified report was finalized.')
        result['events'].append(event('report',state.get('finish_reason','Investigation ended.')));await persist()
    except asyncio.CancelledError:
        if state:
            state.update(status='failed',finish_reason='Investigation interrupted; partial tool history retained.')
            if state['tool_history'] and state['tool_history'][-1]['status']=='running':state['tool_history'][-1]['status']='interrupted'
            await database.save_agent_state(run_id,case_id,state)
        await database.fail_analysis(case_id,'Investigation interrupted; partial agent history retained.');raise
    except TimeoutError:
        if state:
            state.update(status='abstained',finish_reason='Time budget exhausted. No diagnosis was confirmed.')
            if state['tool_history'] and state['tool_history'][-1]['status']=='running':state['tool_history'][-1]['status']='timed_out'
            await persist()
    except Exception:
        if state:
            state.update(status='failed',finish_reason='Agent execution failed. Partial history retained; check local services.')
            await database.save_agent_state(run_id,case_id,state)
        await database.fail_analysis(case_id,'Agent execution failed. Partial history retained; check local services.')
    finally:
        if process and process.returncode is None:
            try:process.kill()
            except ProcessLookupError:pass
            await process.wait()
