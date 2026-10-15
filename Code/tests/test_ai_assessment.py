"""Transport fakes validate software behavior, not real model quality."""
import json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
import ai_assessment as ai
from app import create_app
from engine import load_json
from storage import Store

def fixture_output():
    return {'system_summary':'A smartphone communicates with a gateway to unlock vehicle doors.','assets':[{'id':'A1','name':'Unlock command authenticity','cybersecurity_property':'Authenticity','evidence_ids':['SYS-01']}],'threats':[{'id':'T1','asset_id':'A1','title':'Replay of an unlock request','scenario':'A previously captured request could be replayed if freshness validation is missing.','damage':'Unauthorized vehicle access.','attack_path':'Phone to Bluetooth gateway to body ECU, assuming request capture is possible.','existing_controls':['Authenticated encrypted connection'],'assumptions':['Replay handling is unspecified.'],'evidence_ids':['SYS-01'],'mitigation':'Validate message freshness and bind commands to an authorized credential.','requirement':'The gateway shall reject unlock requests outside the authorized freshness window.','verification':'In a simulator submit a duplicated request and verify it is rejected.'}],'limitations':['Expert review and replay-policy details are required.']}
def mock_ollama(monkeypatch,out=None):
    def fake(path,payload=None,timeout=8):
        if path=='/api/tags':return {'models':[{'name':ai.model_name(),'digest':'TEST-FAKE-NOT-A-REAL-MODEL'}]}
        assert path=='/api/generate';assert isinstance(payload['format'],dict)
        assert 'threat_patterns' not in json.dumps(payload)
        return {'response':json.dumps(out or fixture_output()),'done_reason':'stop','eval_count':100}
    monkeypatch.setattr(ai,'ollama',fake)
@pytest.fixture
def client(tmp_path):
    app=create_app(str(tmp_path/'ai.db'))
    with TestClient(app) as c:yield c
    app.state.ai_pool.shutdown(wait=True);app.state.store.close()
def request_data(id='test-request-001'):
    return {'title':'Bluetooth access','description':'The owner smartphone sends an unlock request through an authenticated encrypted connection to a vehicle Bluetooth gateway and body ECU. Replay handling is unspecified.','max_threats':3,'request_id':id}
def completed(client,id):
    for _ in range(100):
        r=client.get('/api/ai/assessments/'+id).json()
        if r['status'] not in ('Generating','Queued'):return r
        time.sleep(.01)
    raise AssertionError('Job did not complete')
def test_real_path_calls_adapter_and_persists(client,monkeypatch):
    mock_ollama(monkeypatch);r=client.post('/api/ai/generate',json=request_data());assert r.status_code==202
    result=completed(client,r.json()['id']);assert result['status']=='Draft';assert result['output']['assets'][0]['id']=='A1';assert result['model']['model_digest']=='TEST-FAKE-NOT-A-REAL-MODEL'
    assert client.get('/api/ai/assessments').json()[0]['id']==result['id'];assert client.get('/api/ai/assessments/'+result['id']+'/export').json()['output']==result['output']
    assert client.get('/api/ai/status').json()['postgres_active'] is False
    # The new AI route must not populate static template findings.
    assert client.get('/api/state').json()['findings']==[]
def test_bad_citations_fail_without_output(client,monkeypatch):
    out=fixture_output();out['threats'][0]['evidence_ids']=['INVENTED'];mock_ollama(monkeypatch,out)
    r=client.post('/api/ai/generate',json=request_data());result=completed(client,r.json()['id']);assert result['status']=='Failed';assert result['output'] is None
@pytest.mark.parametrize('change',['unknown_asset','duplicate_asset','missing_system_source','excess_threats'])
def test_invalid_model_outputs(change,monkeypatch):
    out=fixture_output();req=request_data();evidence=ai.make_evidence(req['description'],load_json('Input_Data/knowledge_base.json'))
    if change=='unknown_asset':out['threats'][0]['asset_id']='missing'
    if change=='duplicate_asset':out['assets'].append(out['assets'][0])
    if change=='missing_system_source':out['assets'][0]['evidence_ids']=['KB-01']
    if change=='excess_threats':req['max_threats']=1;out['threats'].append({**out['threats'][0],'id':'T2'})
    mock_ollama(monkeypatch,out)
    with pytest.raises(ValueError):ai.generate_draft(req,evidence)
def test_ollama_failure_is_not_canned_success(client,monkeypatch):
    def fail(*a,**k):raise ValueError('Service unavailable')
    monkeypatch.setattr(ai,'ollama',fail);r=client.post('/api/ai/generate',json=request_data());result=completed(client,r.json()['id']);assert result['status']=='Failed';assert result['output'] is None
    assert client.get('/api/ai/status').json()['ready'] is False
def test_idempotency_and_conflict(client,monkeypatch):
    mock_ollama(monkeypatch);body=request_data();client.post('/api/ai/generate',json=body);completed(client,body['request_id']);client.post('/api/ai/generate',json=body)
    assert len(client.get('/api/ai/assessments').json())==1
    body['title']='Different title';assert client.post('/api/ai/generate',json=body).status_code==409
def test_review_saved_and_revision_guard(client,monkeypatch):
    mock_ollama(monkeypatch);client.post('/api/ai/generate',json=request_data());r=completed(client,'test-request-001')
    body={'revision':1,'reviewer':'Test reviewer','decision':'Reviewed','rationale':'Fixture reviewed only for software testing.'};url='/api/ai/assessments/'+r['id']+'/review'
    assert client.post(url,json=body).json()['status']=='Reviewed';assert client.post(url,json=body).status_code==409
    assert client.get('/api/ai/assessments/'+r['id']).json()['review']['reviewer']=='Test reviewer'
def test_short_input_rejected(client):assert client.post('/api/ai/generate',json={**request_data(),'description':'Too short'}).status_code==422
def test_ai_store_survives_restart(tmp_path):
    path=str(tmp_path/'persist.db');s=Store(path);record={'id':'a','title':'Test','status':'Draft','created_at':'2026','updated_at':'2026','output':fixture_output()};s.save_assessment(record);s.close();s=Store(path);assert s.get_assessment('a')==record;s.close()
