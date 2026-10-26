"""Build an explicitly labeled edited replay from actual saved run records/screenshots."""
import json,sys,textwrap,subprocess,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'submission';frames=OUT/'video-frames';frames.mkdir(exist_ok=True)
report=json.loads((OUT/'live-validation.json').read_text());cases={c['name']:c for c in report['cases']}
normal=cases['supported-rice-hypothesis'];uncertain=cases['insufficient-observation']
if any(c['status']=='running' for c in cases.values()):raise SystemExit('Do not render unfinished runs.')
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(font_path,size)
slides=[
 ('AgriSleuth','Track 2 — The Agent That Can Explain Why',['Investigate crop symptoms with traceable evidence.','Explain support, contradictions and what to verify next.','Edited replay of real local runs; waiting time omitted.'],'normal.png'),
 ('A bounded research question','Constructed rice symptom example',['Spindle-shaped lesions; gray-white centers; brown margins.','Reference photograph: USDA ARS / Yulin Jia, D542-1.','A tentative hypothesis is requested, not confirmed diagnosis.'],'normal.png'),
 ('Evidence before a conclusion','Real Zetaris query',['Read-only PostgreSQL JDBC evidence view.',f"Retrieved {len(normal['source_ids'])} cited source excerpts.",'Leading support: '+', '.join(normal['hypotheses'][0]['evidenceIds']) if normal['hypotheses'] else 'No supported hypothesis returned.'],'normal-tools.png'),
 ('The agent chooses its actions',f"Case A: {normal['status']} in {normal['elapsed_seconds']} seconds",[t['tool']+' → '+t['status'] for t in normal['tools']]+['Judge: '+(normal['judge_decisions'][-1]['action'] if normal['judge_decisions'] else 'No verified Judge decision')],'normal-trace.png'),
 ('When observations are insufficient',f"Case B: {uncertain['status']} in {uncertain['elapsed_seconds']} seconds",[('Question: '+uncertain['questions'][0]) if uncertain['questions'] else uncertain.get('finish_reason','No final reason recorded.'),'The displayed outcome is the actual saved result.','No diagnosis accuracy is calculated without ground truth.'],'uncertain.png'),
 ('Sponsor technologies','Working features, not logos',['Zetaris: actual SQL evidence retrieval with source IDs.','Meterless Markovian: bounded actions and compressed checkpoints.','Runtime records and policy/provider tests are saved separately.'],'normal-trace.png'),
 ('Scope and limitations','Evidence-backed research support',['KMA world GTS access returned HTTP 403; weather is unavailable.','No confirmed diagnosis, pesticide advice or measured accuracy claim.','Reproduce: scripts/validate_submission.py; see submission/README.md.'],'uncertain.png')]
for i,(title,subtitle,lines,screenshot) in enumerate(slides):
 im=Image.new('RGB',(1280,720),'#0d2420');d=ImageDraw.Draw(im)
 d.rounded_rectangle((38,35,1242,685),radius=24,fill='#14382f')
 d.text((70,65),title,font=font(43),fill='#f3f7ee');d.text((70,125),subtitle,font=font(24),fill='#b9d8ae')
 y=205
 for line in lines:
  for fragment in textwrap.wrap(line,width=47):d.text((80,y),fragment,font=font(27),fill='#edf4e8');y+=38
  y+=18
 p=OUT/'screenshots'/screenshot
 if p.exists():
  shot=Image.open(p).convert('RGB');shot.thumbnail((310,505));im.paste(shot,(918,168))
 d.text((75,646),'RECORDED REAL RUNS  |  CONSTRUCTED INPUTS  |  NOT DIAGNOSTIC VALIDATION',font=font(16),fill='#c5d4bf')
 im.save(frames/f'{i:02d}.png')
concat=frames/'concat.txt';lines=[]
for i in range(len(slides)):lines.extend(["file '"+str((frames/f'{i:02d}.png').resolve())+"'",'duration 14'])
lines.append("file '"+str((frames/f'{len(slides)-1:02d}.png').resolve())+"'");concat.write_text('\n'.join(lines)+'\n')
try:import imageio_ffmpeg
except ImportError:
 sys.path.insert(0,'/tmp/agrisleuth-media');import imageio_ffmpeg
ffmpeg=os.environ.get('FFMPEG_BINARY') or imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-vf','fps=12,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','23','-threads','2','-movflags','+faststart',str(OUT/'AgriSleuth-Track2-demo.mp4')],check=True)
print('Rendered edited replay:',OUT/'AgriSleuth-Track2-demo.mp4')
