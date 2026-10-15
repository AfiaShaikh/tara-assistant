"""Optional REAL local-model evaluation. Run only after installing and probing Ollama.
No model scores are bundled because this mode was not executed during the build.
Citation metrics do not replace human grading of factual correctness.
"""
import argparse,csv,json,time,subprocess,sys,os
from pathlib import Path
from engine import ROOT,answer,load_json
p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=18);args=p.parse_args()
if not os.getenv('OLLAMA_MODEL'):raise SystemExit('Set OLLAMA_MODEL to an installed exact tag first.')
subprocess.run([sys.executable,str(Path(__file__).with_name('model_probe.py'))],check=True)
kb=load_json('Input_Data/knowledge_base.json');qs=load_json('Input_Data/evaluation_questions.json')[:args.limit];rows=[]
for q in qs:
    start=time.perf_counter()
    try:
        result=answer(q['question'],kb,'ollama');error=None
    except Exception as e:result=None;error=str(e)
    ids=[x['id'] for x in result['citations']] if result else []
    rows.append({**q,'latency_seconds':round(time.perf_counter()-start,3),'result':result,'error':error,'expected_source_cited':q['expected_source'] in ids if q['expected_source'] else None,'human_correctness':None,'human_supported_claims':None})
    print(q['id'],'ERROR' if error else 'completed',flush=True)
out=ROOT/'Evaluation_Results';(out/'actual_llm_results.json').write_text(json.dumps({'model_manifest':load_json('Model_Prompts_Config/actual_model_manifest.json'),'rows':rows,'note':'Actual local run. Human correctness grading remains pending. No aggregate automotive accuracy is inferred.'},indent=2))
with (out/'llm_human_review.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['question_id','question','answer','source_ids','correct_0_1','fully_supported_0_1','reviewer','rationale'])
    for r in rows:w.writerow([r['id'],r['question'],r['result']['answer'] if r['result'] else r['error'],','.join(c['id'] for c in r['result']['citations']) if r['result'] else '', '', '', '', ''])
print('Saved real inference outputs; complete human review before making quality claims.')
