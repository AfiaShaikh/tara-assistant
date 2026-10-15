import base64, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from engine import Architecture, analyze, answer, compare, load_json, risk, vector
from app import create_app
@pytest.fixture
def client(tmp_path):
    app=create_app(str(tmp_path/'test.db'))
    with TestClient(app) as c:yield c
    app.state.store.close()
def test_vector_is_deterministic_normalized():
    a=vector('Firmware authenticity');assert a==vector('Firmware authenticity');assert len(a)==384;assert abs(sum(x*x for x in a)-1)<1e-8
@pytest.mark.parametrize('i,f,score,label',[(1,1,1,'Low'),(1,4,4,'Medium'),(2,4,8,'High'),(3,4,12,'Critical'),(4,4,16,'Critical')])
def test_risk_boundaries(i,f,score,label):assert risk(i,f)=={'score':score,'risk':label}
def test_missing_ratings():assert risk(None,4)['risk']=='Unassessed'
@pytest.mark.parametrize('x',[0,5,True,2.5,'3'])
def test_invalid_rating(x):
    with pytest.raises(ValueError):risk(x,2)
def test_invalid_architecture():
    a=load_json('Input_Data/architecture_v1.json');a['interfaces'][0]['target']='unknown'
    with pytest.raises(ValueError):Architecture.model_validate(a)
def test_duplicate_assets():
    a=load_json('Input_Data/architecture_v1.json');a['assets'].append(a['assets'][0])
    with pytest.raises(ValueError):Architecture.model_validate(a)
def test_patterns_and_controls():
    a=load_json('Input_Data/architecture_v1.json');fs=analyze(a,load_json('Input_Data/threat_patterns.json'))
    assert len(fs)==4;assert all(f['risk']=='Unassessed' for f in fs)
    assert fs[0]['documented_controls']==['Package signature verification']
    assert fs[0]['candidate_paths']==[['IF-01','IF-02']]
def test_grounding_and_abstention():
    kb=load_json('Input_Data/knowledge_base.json')
    r=answer('How do we prevent firmware rollback?',kb)
    assert r['citations'][0]['id']=='KB-02';assert r['answer']==r['citations'][0]['text']
    assert answer('weather Pune tomorrow',kb)['abstained']
def test_workflow_review_conflict_and_persistence(client):
    fs=client.post('/api/analyze',json={}).json();f=fs[0]
    payload=dict(revision=1,impact=3,feasibility=2,status='Accepted',reviewer='Demo reviewer',rationale='Synthetic ratings for functional test only.')
    r=client.post('/api/findings/'+f['id']+'/review',json=payload);assert r.status_code==200;assert r.json()['risk']=='Medium'
    assert client.post('/api/findings/'+f['id']+'/review',json=payload).status_code==409
    again=client.post('/api/analyze',json={}).json();assert next(x for x in again if x['id']==f['id'])['status']=='Accepted'
    assert any(e['action']=='review' for e in client.get('/api/audit').json())
def test_unrated_acceptance_rejected(client):
    f=client.post('/api/analyze',json={}).json()[0]
    r=client.post('/api/findings/'+f['id']+'/review',json=dict(revision=1,status='Accepted',reviewer='Demo',rationale='Missing ratings'))
    assert r.status_code==422
def test_change_impact_marks_stale(client):
    fs=client.post('/api/analyze',json={}).json()
    assert client.post('/api/architecture',json=load_json('Input_Data/architecture_v2.json')).status_code==200
    d=client.post('/api/compare',json={'old_version':'1.0','new_version':'2.0','mark_stale':True}).json()
    assert len(d['changes'])==2;assert len(d['affected_findings'])==3
    assert len(client.post('/api/analyze',json={}).json())==5
    client.post('/api/select',json={'version':'1.0'})
    old=client.get('/api/state').json()['findings'];assert sum(f['needs_reassessment'] for f in old)==3
    stale=next(f for f in old if f['needs_reassessment'])
    r=client.post('/api/findings/'+stale['id']+'/review',json=dict(revision=stale['revision'],impact=3,feasibility=2,status='Accepted',reviewer='Demo',rationale='Cannot reuse stale review'))
    assert r.status_code==409
def test_version_is_immutable(client):
    a=load_json('Input_Data/architecture_v1.json');a['description']='Changed';assert client.post('/api/architecture',json=a).status_code==409
def test_document_ingestion_and_citation(client):
    r=client.post('/api/documents',json={'name':'Extra.md','text':'Unique zephyr key rotation requires a quarterly audit.'});assert r.status_code==200
    a=client.post('/api/ask',json={'question':'zephyr rotation quarterly'}).json();assert a['citations'][0]['source']=='Extra.md'
def test_pdf_rejection(client):
    assert client.post('/api/documents',json={'name':'bad.pdf','pdf_base64':base64.b64encode(b'not pdf').decode()}).status_code==422
def test_cross_origin_write(client):assert client.post('/api/analyze',json={},headers={'Origin':'https://attacker.example'}).status_code==403
def test_export(client):
    client.post('/api/analyze',json={});r=client.get('/api/export/csv');assert r.status_code==200;assert 'requirement' in r.text
    assert len(client.get('/api/export/json').json()['findings'])==4
def test_missing_ollama_is_explicit(client,monkeypatch):
    monkeypatch.delenv('OLLAMA_MODEL',raising=False)
    r=client.post('/api/ask',json={'question':'Firmware rollback','mode':'ollama'});assert r.status_code==502;assert 'required' in r.json()['detail']
def test_invalid_llm_citations_rejected(monkeypatch):
    import io,urllib.request
    monkeypatch.setenv('OLLAMA_MODEL','mock-only')
    class Fake(io.BytesIO):pass
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:Fake(json.dumps({'response':json.dumps({'answer':'Unsupported claim','citation_ids':['INVENTED']})}).encode()))
    with pytest.raises(ValueError):answer('rollback',load_json('Input_Data/knowledge_base.json'),'ollama')
def test_restart_preserves_state(tmp_path):
    path=str(tmp_path/'persist.db');app=create_app(path)
    with TestClient(app) as c:c.post('/api/analyze',json={})
    app.state.store.close();app2=create_app(path)
    with TestClient(app2) as c:assert len(c.get('/api/state').json()['findings'])==4
    app2.state.store.close()
