"""Reproducible small synthetic benchmark. Not an expert accuracy claim."""
import json,sys,time,platform,importlib.metadata
from engine import ROOT,load_json,retrieve,answer,analyze,compare
out=ROOT/'Evaluation_Results';out.mkdir(exist_ok=True)
kb=load_json('Input_Data/knowledge_base.json');qs=load_json('Input_Data/evaluation_questions.json');rows=[]
for q in qs:
    t=time.perf_counter();hits=retrieve(q['question'],kb);a=answer(q['question'],kb)
    ids=[h['id'] for h in hits];expected=q['expected_source']
    rows.append({**q,'retrieved':ids,'top1_correct':bool(ids and ids[0]==expected) if expected else a['abstained'],'recall_at_3':expected in ids if expected else None,'reciprocal_rank':1/(ids.index(expected)+1) if expected in ids else 0,'citation_resolves':all(c['id'] in {k['id'] for k in kb} for c in a['citations']),'latency_ms':round((time.perf_counter()-t)*1000,3),'output':a})
positive=[r for r in rows if r['expected_source']];negative=[r for r in rows if not r['expected_source']]
metrics={'evaluation_mode':'offline-extractive + deterministic patterns','dataset':'Synthetic self-authored set; not independent/expert-validated','positive_questions':len(positive),'abstention_questions':len(negative),'top1_accuracy':sum(r['top1_correct'] for r in positive)/len(positive),'recall_at_3':sum(r['recall_at_3'] for r in positive)/len(positive),'mrr_at_3':sum(r['reciprocal_rank'] for r in positive)/len(positive),'abstention_accuracy':sum(r['top1_correct'] for r in negative)/len(negative),'citation_resolution_rate':sum(r['citation_resolves'] for r in rows)/len(rows),'mean_latency_ms':sum(r['latency_ms'] for r in rows)/len(rows),'llm_evaluated':False,'postgres_evaluated':False,'limits':['Citation resolution is not semantic correctness.','Small synthetic corpus and questions share an author.','No expert threat-coverage or risk-validity benchmark.','End-to-end Ollama and PostgreSQL were not exercised.']}
for split in ('smoke','challenge'):
    subset=[r for r in positive if r['split']==split];metrics[split+'_top1_accuracy']=sum(r['top1_correct'] for r in subset)/len(subset)
a=load_json('Input_Data/architecture_v1.json');b=load_json('Input_Data/architecture_v2.json');fs=analyze(a,load_json('Input_Data/threat_patterns.json'))
for name,value in [('metrics.json',metrics),('retrieval_results.json',rows),('sample_tara_v1.json',fs),('sample_change_impact.json',compare(a,b,fs))]: (out/name).write_text(json.dumps(value,indent=2))
env={'python':platform.python_version(),'platform':platform.platform(),'packages':{x:importlib.metadata.version(x) for x in ['fastapi','uvicorn','pydantic','pypdf','httpx','pytest','psycopg']}}
(out/'tested_environment.json').write_text(json.dumps(env,indent=2))
print(json.dumps(metrics,indent=2))
