"""Deterministic TARA prototype core. No vehicle/network attack execution."""
from __future__ import annotations
import hashlib, json, math, re, os, urllib.request
from collections import Counter, deque
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
ROOT = Path(__file__).resolve().parents[1]
DIM = 384
STOP=set('a an the and or is are to of in for with how what should do does we it be on from can as by this that'.split())
def tokens(text): return [x for x in re.findall(r'[a-z0-9]+',text.lower()) if x not in STOP]
def vector(text):
    v=[0.0]*DIM
    for t in tokens(text):
        h=hashlib.sha256(t.encode()).digest();v[int.from_bytes(h[:4],'big')%DIM]+=1 if h[4]%2 else -1
    norm=math.sqrt(sum(x*x for x in v)) or 1
    return [x/norm for x in v]
def fingerprint(x): return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def load_json(name): return json.loads((ROOT/name).read_text())
class Component(BaseModel):
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,60}$');name:str=Field(min_length=1,max_length=200);zone:str=Field(min_length=1,max_length=100)
class Interface(BaseModel):
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,60}$');name:str;source:str;target:str;protocol:str;exposed:bool;controls:list[str]=Field(default_factory=list)
class Asset(BaseModel):
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,60}$');name:str;component:str;tags:list[str];controls:list[str]=Field(default_factory=list)
class Architecture(BaseModel):
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,60}$');version:str=Field(min_length=1,max_length=40);title:str;classification:str='SYNTHETIC';description:str=''
    components:list[Component]=Field(min_length=1,max_length=100)
    interfaces:list[Interface]=Field(default_factory=list,max_length=200)
    assets:list[Asset]=Field(min_length=1,max_length=200)
    assumptions:list[str]=Field(default_factory=list)
    @model_validator(mode='after')
    def links(self):
        cs={c.id for c in self.components}
        for name in ('components','interfaces','assets'):
            rows=getattr(self,name)
            if len({r.id for r in rows})!=len(rows):raise ValueError(f'Duplicate IDs in {name}')
        if any(i.source not in cs or i.target not in cs for i in self.interfaces):raise ValueError('Unknown interface endpoint')
        if any(a.component not in cs for a in self.assets):raise ValueError('Unknown asset component')
        return self

def retrieve(question, chunks, k=3):
    qt=tokens(question)
    if not qt or not chunks:return []
    docs=[tokens(c['title']+' '+c['text']) for c in chunks]; n=len(docs);avg=sum(map(len,docs))/n
    freq=Counter(t for d in docs for t in set(d));qv=vector(question);scored=[]
    for chunk,d in zip(chunks,docs):
        cnt=Counter(d);bm=0
        for t in set(qt):
            tf=cnt[t]
            if tf:bm+=math.log(1+(n-freq[t]+0.5)/(freq[t]+0.5))*tf*2.5/(tf+1.5*(.25+.75*len(d)/avg))
        if bm<=0:continue
        cosine=sum(a*b for a,b in zip(qv,vector(chunk['title']+' '+chunk['text'])))
        scored.append({**chunk,'score':round(bm+.25*cosine,5)})
    return sorted(scored,key=lambda x:(-x['score'],x['id']))[:k]

def answer(question,chunks,mode='offline'):
    hits=retrieve(question,chunks)
    if not hits:return {'answer':'Insufficient evidence in the project knowledge base.','citations':[],'abstained':True,'mode':mode}
    if mode=='offline':
        # Extract, never present fixed prose as an LLM generation.
        h=hits[0]
        return {'answer':h['text'],'citations':[h],'abstained':False,'mode':'offline-extractive'}
    model=os.getenv('OLLAMA_MODEL')
    if not model:raise ValueError('OLLAMA_MODEL is required; offline mode remains available.')
    prompt=(ROOT/'Model_Prompts_Config/system_prompt.txt').read_text()
    payload={'model':model,'stream':False,'format':'json','options':{'temperature':0},'system':prompt,'prompt':json.dumps({'question':question,'evidence':hits})}
    req=urllib.request.Request(os.getenv('OLLAMA_URL','http://127.0.0.1:11434')+'/api/generate',json.dumps(payload).encode(),{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as response: result=json.load(response)
    try:
        draft=json.loads(result['response']);ids=draft['citation_ids'];body=draft['answer']
        if not isinstance(body,str) or not isinstance(ids,list) or any(not isinstance(x,str) for x in ids):raise ValueError()
        allowed={h['id'] for h in hits}
        if not ids or not set(ids)<=allowed:raise ValueError()
    except (KeyError,ValueError,TypeError):raise ValueError('Model response failed citation/schema validation; no answer accepted.')
    return {'answer':body,'citations':[h for h in hits if h['id'] in ids],'abstained':False,'mode':'ollama','model':model,'notice':'Citation membership checked; factual entailment still requires review.'}

def candidate_paths(arch,target):
    paths=[]
    for edge in arch['interfaces']:
        if not edge['exposed']:continue
        queue=deque([(edge['target'],[edge['id']],{edge['source'],edge['target']})])
        while queue and len(paths)<12:
            node,seq,visited=queue.popleft()
            if node==target:paths.append(seq);continue
            for nxt in arch['interfaces']:
                if nxt['source']==node and nxt['target'] not in visited:
                    queue.append((nxt['target'],seq+[nxt['id']],visited|{nxt['target']}))
    return paths

def analyze(arch,patterns):
    rev=fingerprint(arch);findings=[]
    for a in arch['assets']:
        for p in patterns:
            if p['tag'] not in a['tags']:continue
            fid='F-'+hashlib.sha256((rev+a['id']+p['id']).encode()).hexdigest()[:10]
            findings.append({'id':fid,'architecture_hash':rev,'architecture_version':arch['version'],'asset_id':a['id'],'asset_name':a['name'],'component':a['component'],'pattern_id':p['id'],'title':p['title'],'scenario':p['scenario'],'damage':p['damage'],'mitigation':p['mitigation'],'requirement':p['requirement'],'test':p['test'],'assumptions':[p['assumption']],'documented_controls':a['controls'],'citations':[p['evidence_id'],f"ARCH:{arch['version']}#/assets/{a['id']}"],'candidate_paths':candidate_paths(arch,a['component']),'path_notice':'Connectivity hypothesis only; controls and prerequisites not evaluated.','impact':None,'feasibility':None,'score':None,'risk':'Unassessed','risk_policy':'DEMO-RISK-v1','rationale':'','reviewer':'','status':'Draft','revision':1,'needs_reassessment':False})
    return findings

def risk(impact,feasibility):
    if impact is None or feasibility is None:return {'score':None,'risk':'Unassessed'}
    if type(impact)!=int or type(feasibility)!=int or not 1<=impact<=4 or not 1<=feasibility<=4:raise ValueError('Ratings must be integers 1..4')
    score=impact*feasibility
    for ceiling,label in load_json('Model_Prompts_Config/risk_policy.json')['thresholds']:
        if score<=ceiling:return {'score':score,'risk':label}

def compare(old,new,findings):
    changes=[];seeds=set()
    for group in ('components','interfaces','assets'):
        a={x['id']:x for x in old[group]};b={x['id']:x for x in new[group]}
        for key in sorted(a.keys()|b.keys()):
            if a.get(key)==b.get(key):continue
            changes.append({'kind':group,'id':key,'change':'added' if key not in a else 'removed' if key not in b else 'modified','before':a.get(key),'after':b.get(key)})
            for row in (a.get(key),b.get(key)):
                if row:seeds.update([row['id']] if group=='components' else [row['component']] if group=='assets' else [row['source'],row['target']])
    if any(old.get(k)!=new.get(k) for k in ('assumptions','description','classification')):
        changes.append({'kind':'context','id':'item','change':'modified'});seeds.update(c['id'] for c in old['components']+new['components'])
    affected=set(seeds)
    for _ in range(len(old['components'])+len(new['components'])):
        for e in old['interfaces']+new['interfaces']:
            if e['source'] in affected:affected.add(e['target'])
    return {'changes':changes,'affected_components':sorted(affected),'affected_findings':[f['id'] for f in findings if f['component'] in affected],'notice':'Conservative forward dependency analysis; expert review may identify additional impacts.'}
