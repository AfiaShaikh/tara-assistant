import csv, io, json, os, re, uuid, base64
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from engine import ROOT, Architecture, analyze, answer, compare, fingerprint, load_json, risk
from storage import Store

def create_app(db_path=None):
    app=FastAPI(title='TARA Studio',version='1.1.0',docs_url=None,redoc_url=None);s=Store(db_path or os.getenv('TARA_DB',str(ROOT/'Code/runtime/tara.db')));app.state.store=s
    for chunk in load_json('Input_Data/knowledge_base.json'):
        if not s.get('chunk',chunk['id']):s.put('chunk',chunk['id'],chunk)
    if not s.all('architecture'):
        a=load_json('Input_Data/architecture_v1.json');s.put('architecture',a['version'],a);s.put('meta','active',{'version':a['version']})
    def event(action,details):
        id=str(uuid.uuid4());s.put('event',id,{'id':id,'time':datetime.now(timezone.utc).isoformat(),'action':action,'details':details})
    def active():return s.get('architecture',s.get('meta','active')['version'])
    def findings():return [f for f in s.all('finding') if f['architecture_hash']==fingerprint(active())]
    @app.middleware('http')
    async def protect(request:Request,call_next):
        if request.method in ('POST','PUT','DELETE'):
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/'):
                return Response('Cross-origin writes blocked',status_code=403)
            if int(request.headers.get('content-length','0'))>8_000_000:return Response('Upload too large',status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        return response
    @app.get('/')
    def index():return FileResponse(Path(__file__).parent/'static/index.html')
    app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
    @app.get('/api/state')
    def state():return {'architecture':active(),'versions':[x['version'] for x in s.all('architecture')],'findings':findings(),'knowledge':s.all('chunk'),'database':'PostgreSQL + pgvector' if s.pg else 'SQLite','mode':'Offline baseline; optional Ollama','policy':load_json('Model_Prompts_Config/risk_policy.json')}
    @app.post('/api/architecture')
    def upload(a:Architecture):
        data=a.model_dump()
        with s.lock:
            current=active()
            if data['id']!=current['id']:raise HTTPException(400,'This workspace accepts versions of '+current['id']+' only.')
            prior=s.get('architecture',a.version)
            if prior and fingerprint(prior)!=fingerprint(data):raise HTTPException(409,'Version already exists with different content; use a new version.')
            s.put('architecture',a.version,data);s.put('meta','active',{'version':a.version});event('architecture_selected',{'version':a.version,'hash':fingerprint(data)})
        return data
    class Select(BaseModel):version:str
    @app.post('/api/select')
    def select(x:Select):
        if not s.get('architecture',x.version):raise HTTPException(404,'Unknown version')
        s.put('meta','active',x.model_dump());return {'ok':True}
    @app.get('/api/sample/{version}')
    def sample(version:str):
        if version not in ('1','2'):raise HTTPException(404)
        return load_json(f'Input_Data/architecture_v{version}.json')
    @app.post('/api/analyze')
    def run():
        with s.lock:
            a=active()
            for f in analyze(a,load_json('Input_Data/threat_patterns.json')):
                if not s.get('finding',f['id']):s.put('finding',f['id'],f)
            event('analysis',{'version':a['version'],'mode':'deterministic-pattern-matching','count':len(findings())})
            return findings()
    class Review(BaseModel):
        revision:int;impact:int|None=Field(default=None,ge=1,le=4,strict=True);feasibility:int|None=Field(default=None,ge=1,le=4,strict=True)
        status:Literal['Draft','Accepted','Rejected']='Draft';rationale:str=Field(min_length=5,max_length=3000);reviewer:str=Field(min_length=2,max_length=100)
    @app.post('/api/findings/{id}/review')
    def review(id:str,x:Review):
        with s.lock:
            f=s.get('finding',id)
            if not f:raise HTTPException(404,'Finding not found')
            if f['architecture_hash']!=fingerprint(active()):raise HTTPException(409,'Select the finding architecture before reviewing.')
            if f['needs_reassessment'] and x.status=='Accepted':raise HTTPException(409,'Stale finding cannot be accepted; review the new architecture instead.')
            if f['revision']!=x.revision:raise HTTPException(409,'Finding changed; reload before saving.')
            if x.status=='Accepted' and (x.impact is None or x.feasibility is None):raise HTTPException(422,'Accepted findings require both ratings.')
            before=dict(f);f.update(x.model_dump());f.update(risk(x.impact,x.feasibility));f['revision']+=1
            s.put('finding',id,f);event('review',{'before':before,'after':f});return f
    class Query(BaseModel):question:str=Field(min_length=3,max_length=1500);mode:Literal['offline','ollama']='offline'
    @app.post('/api/ask')
    def ask(q:Query):
        try:result=answer(q.question,s.candidates(q.question),q.mode)
        except Exception as e:raise HTTPException(502,'Model unavailable or rejected response: '+str(e)[:200])
        event('question',{'question':q.question,'mode':result['mode'],'sources':[x['id'] for x in result['citations']]});return result
    class Compare(BaseModel):old_version:str;new_version:str;mark_stale:bool=False
    @app.post('/api/compare')
    def diff(x:Compare):
        with s.lock:
            old=s.get('architecture',x.old_version);new=s.get('architecture',x.new_version)
            if not old or not new:raise HTTPException(404,'Both versions must be imported')
            fs=[f for f in s.all('finding') if f['architecture_hash']==fingerprint(old)];result=compare(old,new,fs)
            if x.mark_stale:
                for f in fs:
                    if f['id'] in result['affected_findings']:
                        f['needs_reassessment']=True;f['status']='Needs reassessment';f['revision']+=1;s.put('finding',f['id'],f)
                event('change_impact',{'old':x.old_version,'new':x.new_version,**result})
            return result
    class Document(BaseModel):name:str=Field(min_length=1,max_length=100);text:str=Field(default='',max_length=150000);pdf_base64:str|None=Field(default=None,max_length=7000000)
    @app.post('/api/documents')
    def document(x:Document):
        pages=[(1,x.text)]
        if x.pdf_base64:
            try:
                from pypdf import PdfReader
                raw=base64.b64decode(x.pdf_base64,validate=True)
                if len(raw)>5_000_000:raise ValueError('PDF exceeds 5 MB')
                reader=PdfReader(io.BytesIO(raw))
                if len(reader.pages)>100:raise ValueError('Maximum 100 pages')
                pages=[(i+1,p.extract_text() or '') for i,p in enumerate(reader.pages)]
            except Exception as e:raise HTTPException(422,'Cannot extract PDF: '+str(e)[:100])
        if sum(len(t) for _,t in pages)>150000:raise HTTPException(422,'Extracted text exceeds 150,000 characters')
        docs=[]
        for page,text in pages:
            for n,start in enumerate(range(0,len(text),1100)):
                body=text[start:start+1200].strip()
                if not body:continue
                id='DOC-'+fingerprint([x.name,page,n,body])[:12]
                docs.append({'id':id,'title':x.name,'text':body,'source':x.name,'locator':f'page {page}, chunk {n+1}','classification':'USER-SUPPLIED / UNREVIEWED','version':'content-addressed'})
        if not docs:raise HTTPException(422,'No extractable text. Scanned PDFs need OCR before upload.')
        for d in docs:s.put('chunk',d['id'],d)
        event('document_ingestion',{'name':x.name,'chunks':len(docs)});return {'chunks':len(docs)}
    @app.get('/api/evaluation')
    def evaluation():
        return {'metrics':load_json('Evaluation_Results/metrics.json'),'results':load_json('Evaluation_Results/retrieval_results.json')}
    @app.get('/api/audit')
    def audit():return sorted(s.all('event'),key=lambda x:x['time'],reverse=True)
    @app.get('/api/export/{format}')
    def export(format:str):
        fs=findings()
        if format=='json':return {'architecture':active(),'findings':fs,'notice':'Synthetic educational analysis; expert approval pending.'}
        if format!='csv':raise HTTPException(404)
        out=io.StringIO();fields=['id','asset_id','title','scenario','damage','risk','score','status','requirement','test','citations'];writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
        for f in fs:
            row={k:json.dumps(f[k]) if isinstance(f[k],list) else f.get(k,'') for k in fields}
            row={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()};writer.writerow(row)
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=tara_register.csv'})
    from ai_assessment import attach_ai_routes
    attach_ai_routes(app,s,event)
    return app
app=create_app()
