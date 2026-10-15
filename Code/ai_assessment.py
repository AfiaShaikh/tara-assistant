"""Real Ollama-generated TARA drafts. No canned-output or offline fallback."""
import json, os, time, uuid, hashlib, urllib.request, urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from fastapi import HTTPException
from fastapi.responses import Response
from engine import ROOT, retrieve

def now():return datetime.now(timezone.utc).isoformat()
def model_name():return os.getenv('OLLAMA_MODEL','qwen2.5:3b-instruct')
def ollama(path,payload=None,timeout=8):
    url=os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+path
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data,{'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read(300).decode(errors='replace')
        raise ValueError(f'Ollama HTTP {e.code}: {body}') from e
    except (urllib.error.URLError,TimeoutError) as e:raise ValueError('Cannot reach Ollama or inference timed out. Check Ollama service, installed model and OLLAMA_URL.') from e

def model_status():
    name=model_name()
    try:
        models=ollama('/api/tags').get('models',[])
        found=next((m for m in models if m.get('name')==name or m.get('model')==name),None)
        return {'reachable':True,'ready':bool(found),'model':name,'digest':found.get('digest') if found else None,'installed_models':[m['name'] for m in models],'message':'Ready for generation' if found else f'Model is missing. Run: ollama pull {name}'}
    except Exception as e:return {'reachable':False,'ready':False,'model':name,'digest':None,'message':str(e)}
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class AIAsset(Strict):
    id:str=Field(min_length=1,max_length=50)
    name:str=Field(min_length=2,max_length=200)
    cybersecurity_property:Literal['Integrity','Confidentiality','Availability','Authenticity','Authorization']
    evidence_ids:list[str]=Field(min_length=1,max_length=8)
class AIThreat(Strict):
    id:str=Field(min_length=1,max_length=50)
    asset_id:str
    title:str=Field(min_length=3,max_length=200)
    scenario:str=Field(min_length=10,max_length=1500)
    damage:str=Field(min_length=5,max_length=1000)
    attack_path:str=Field(min_length=5,max_length=1000)
    existing_controls:list[str]=Field(max_length=8)
    assumptions:list[str]=Field(min_length=1,max_length=8)
    evidence_ids:list[str]=Field(min_length=1,max_length=8)
    mitigation:str=Field(min_length=5,max_length=1200)
    requirement:str=Field(min_length=5,max_length=1200)
    verification:str=Field(min_length=5,max_length=1200)
class DraftAssessment(Strict):
    system_summary:str=Field(min_length=20,max_length=2000)
    assets:list[AIAsset]=Field(min_length=1,max_length=8)
    threats:list[AIThreat]=Field(min_length=1,max_length=6)
    limitations:list[str]=Field(min_length=1,max_length=8)
    @model_validator(mode='after')
    def links(self):
        ids={a.id for a in self.assets}
        if len(ids)!=len(self.assets):raise ValueError('Duplicate asset IDs')
        if len({t.id for t in self.threats})!=len(self.threats):raise ValueError('Duplicate threat IDs')
        if any(t.asset_id not in ids for t in self.threats):raise ValueError('Threat refers to an unknown asset')
        return self
class GenerateRequest(Strict):
    title:str=Field(min_length=3,max_length=160)
    description:str=Field(min_length=100,max_length=8000)
    max_threats:int=Field(default=3,ge=1,le=6,strict=True)
    request_id:str=Field(default_factory=lambda:str(uuid.uuid4()),pattern=r'^[a-zA-Z0-9_-]{8,80}$')
class AssessmentReview(Strict):
    revision:int
    reviewer:str=Field(min_length=2,max_length=100)
    decision:Literal['Reviewed','Rejected']
    rationale:str=Field(min_length=10,max_length=3000)

def make_evidence(description,chunks):
    # Non-overlapping user-description chunks keep citations traceable to exact text.
    supplied=[{'id':f'SYS-{i//1000+1:02}','title':'Submitted system description','text':description[i:i+1000],'source':'User input','locator':f'characters {i+1}-{min(i+1000,len(description))}'} for i in range(0,len(description),1000)]
    references=retrieve(description,chunks,k=4)
    return supplied+[{k:h[k] for k in ('id','title','text','source','locator')} for h in references]

def generate_draft(request,evidence):
    status=model_status()
    if not status['ready']:raise ValueError(status['message'])
    prompt=(ROOT/'Model_Prompts_Config/assessment_system_prompt.txt').read_text()
    task={'task':'Generate a NEW draft automotive cybersecurity assessment for the submitted system.','title':request['title'],'maximum_threats':request['max_threats'],'evidence':evidence}
    payload={'model':model_name(),'stream':False,'format':DraftAssessment.model_json_schema(),'system':prompt,'prompt':json.dumps(task),'options':{'temperature':0,'num_ctx':8192,'num_predict':4096},'keep_alive':'10m'}
    start=time.perf_counter()
    raw=ollama('/api/generate',payload,timeout=int(os.getenv('OLLAMA_TIMEOUT','600')))
    if raw.get('done_reason')=='length':raise ValueError('Model reached its output limit. Reduce the requested threats to 1 or 2 and try again.')
    try:draft=DraftAssessment.model_validate_json(raw.get('response',''))
    except Exception as e:raise ValueError('Generated output failed schema validation; nothing was accepted. Try fewer threats or a more explicit description. '+str(e)[:250]) from e
    allowed={e['id'] for e in evidence};sys_ids={e['id'] for e in evidence if e['id'].startswith('SYS-')}
    if len(draft.threats)>request['max_threats']:raise ValueError('Model exceeded requested threat count; draft rejected.')
    for asset in draft.assets:
        if not set(asset.evidence_ids)<=allowed or not set(asset.evidence_ids)&sys_ids:raise ValueError('Asset has unknown citations or lacks submitted-system evidence; draft rejected.')
    for threat in draft.threats:
        if not set(threat.evidence_ids)<=allowed or not set(threat.evidence_ids)&sys_ids:raise ValueError('Threat has unknown citations or lacks submitted-system evidence; draft rejected.')
    metadata={'provider':'Ollama','model':model_name(),'model_digest':status['digest'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'temperature':0,'elapsed_seconds':round(time.perf_counter()-start,2),'eval_count':raw.get('eval_count'),'prompt_eval_count':raw.get('prompt_eval_count'),'done_reason':raw.get('done_reason'),'response_sha256':hashlib.sha256(raw.get('response','').encode()).hexdigest()}
    return draft.model_dump(),metadata

def attach_ai_routes(app,s,event):
    pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='tara-llm')
    app.state.ai_pool=pool
    # An interrupted job must not appear to run forever after a process restart.
    for old in s.list_assessments():
        if old['status'] in ('Queued','Generating'):
            old.update(status='Failed',error='Application restarted during generation. Submit again.',updated_at=now());s.save_assessment(old)
    def perform(id,req,evidence):
        record=s.get_assessment(id)
        record.update(status='Generating',updated_at=now());s.save_assessment(record)
        try:
            draft,metadata=generate_draft(req,evidence)
            record.update(status='Draft',output=draft,model=metadata,error=None,updated_at=now())
            s.save_assessment(record)
            event('ai_assessment_generated',{'assessment_id':id,'model':metadata['model'],'digest':metadata['model_digest'],'threats':len(draft['threats']),'database':'PostgreSQL' if s.pg else 'SQLite'})
        except Exception as e:
            record.update(status='Failed',error=str(e)[:700],updated_at=now());s.save_assessment(record)
            event('ai_assessment_failed',{'assessment_id':id,'error':record['error']})
    @app.get('/api/ai/status')
    def status():return {**model_status(),'database':'PostgreSQL + pgvector' if s.pg else 'SQLite (local fallback)','postgres_active':s.pg,'table':'ai_assessments','notice':'No offline or canned fallback for AI assessment generation.'}
    @app.post('/api/ai/generate',status_code=202)
    def generate(req:GenerateRequest):
        with s.lock:
            existing=s.get_assessment(req.request_id)
            if existing:
                if existing['input']!=req.model_dump():raise HTTPException(409,'Request ID already used for different input.')
                return existing
            if any(r['status'] in ('Queued','Generating') for r in s.list_assessments()):raise HTTPException(409,'An assessment is already generating. Wait for it to finish.')
            # Snapshot sources before inference: later edits cannot change citations.
            evidence=make_evidence(req.description,s.candidates(req.description))
            record={'id':req.request_id,'title':req.title,'status':'Queued','revision':1,'created_at':now(),'updated_at':now(),'input':req.model_dump(),'evidence':evidence,'output':None,'model':{'provider':'Ollama','model':model_name()},'review':None,'error':None,'risk':'Unassessed','notice':'LLM-generated draft; citation IDs checked, meaning and completeness require human review.'}
            s.save_assessment(record);pool.submit(perform,record['id'],req.model_dump(),evidence)
            return record
    @app.get('/api/ai/assessments')
    def listing():return [{'id':r['id'],'title':r['title'],'status':r['status'],'created_at':r['created_at'],'model':r['model'],'revision':r['revision']} for r in s.list_assessments()]
    @app.get('/api/ai/assessments/{id}')
    def read(id:str):
        r=s.get_assessment(id)
        if not r:raise HTTPException(404,'Assessment not found')
        return r
    @app.post('/api/ai/assessments/{id}/review')
    def review(id:str,x:AssessmentReview):
        with s.lock:
            r=read(id)
            if not r.get('output'):raise HTTPException(409,'No successful output to review')
            if r['revision']!=x.revision:raise HTTPException(409,'Assessment changed; reload before reviewing')
            previous=r.get('review');r.update(status=x.decision,review={**x.model_dump(),'time':now()},revision=r['revision']+1,updated_at=now());s.save_assessment(r)
            event('ai_assessment_review',{'assessment_id':id,'previous_review':previous,'review':r['review']});return r
    @app.get('/api/ai/assessments/{id}/export')
    def export(id:str):
        r=read(id)
        return Response(json.dumps(r,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename=ai_assessment.json'})
