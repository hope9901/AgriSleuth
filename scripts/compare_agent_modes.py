"""Compare a live single-pass baseline with a saved autonomous run. No accuracy without labels."""
import argparse,asyncio,json,sys,time
from pathlib import Path
from uuid import UUID
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'critic'))
from config import load_environment
load_environment()
import database
from pipeline import generate
from retrieval import retrieve,rank_evidence
from evaluation import compare_modes
async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--investigation',required=True,type=UUID)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    case=await database.analysis_case(args.investigation)
    state=await database.read_agent_state(args.investigation)
    if not case or not state:raise SystemExit('A saved autonomous investigation is required.')
    start=time.monotonic();rows=await retrieve(case['crop']);evidence=rank_evidence(rows,case['symptoms']+' '+case['affected_part'])
    if not evidence:raise SystemExit('No evidence for a baseline; comparison not generated.')
    weather=await database.read_weather(args.investigation)
    case['weather_context']={k:(weather or {}).get(k) for k in ('status','observed_date','summary','limitations')}
    proposal=await generate(case,evidence,'',None)
    report=compare_modes(dict(candidates=proposal.model_dump()['candidates'],steps=1,tool_calls=1,elapsed_seconds=round(time.monotonic()-start,2)),state)
    report['baseline_mode']='Actual single-pass Diagnosis + Zetaris DB + saved weather; no Critic/Controller'
    report['caveat']='Same user input; source versions and available weather may differ from the saved run. Not a controlled causal study.'
    text=json.dumps(report,indent=2)
    if args.output:args.output.write_text(text+'\n')
    else:print(text)
if __name__=='__main__':asyncio.run(main())
