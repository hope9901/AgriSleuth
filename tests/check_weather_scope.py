"""Review context selection never changes the source weather assessment."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'critic'))
from environment import review_weather_context
weather=dict(status='partial',observed_date='2026-07-18',environment_assessments=[dict(disease_id='rice_001',assessment='insufficient_for_infection_assessment',required_inputs=['Heading date','Transplanting date','Region','Cultivar'],checks=[],windows=[dict(window_id='leaf',core=True,applies_to='Leaf-blast infection assessment',coverage='incomplete'),dict(window_id='panicle',core=True,applies_to='Panicle-blast infection window',coverage='anchor_input_required')])])
original=copy.deepcopy(weather)
context=review_weather_context(weather,dict(growth_stage='vegetative',affected_part='leaf',region='Seoul'),{'rice_001'})
assessment=context['environment_assessments'][0]
assert [w['window_id'] for w in assessment['windows']]==['leaf']
assert assessment['infection_model_inputs']==['Transplanting date','Cultivar']
assert 'do not by themselves block' in assessment['interpretation']
assert weather==original
for case in ({},dict(growth_stage='reproductive',affected_part='panicle'),dict(growth_stage='unknown',affected_part='leaf')):
 a=review_weather_context(weather,case,{'rice_001'})['environment_assessments'][0]
 assert len(a['windows'])==2 and 'Heading date' in a['infection_model_inputs']
assert review_weather_context(weather,{}, {'maize_013'})['environment_assessments']==[]
assert len(json.dumps(context))<2000
print('PASS stage-specific windows, known-region exclusion, unknown-stage conservatism, input scope, original-source preservation and review budget')
