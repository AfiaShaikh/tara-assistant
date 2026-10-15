"""Record actual local Ollama identity; no model download is performed."""
import json,os,urllib.request
from pathlib import Path
url=os.getenv('OLLAMA_URL','http://127.0.0.1:11434');name=os.environ['OLLAMA_MODEL']
with urllib.request.urlopen(url+'/api/tags',timeout=10) as r: tags=json.load(r)['models']
match=next((x for x in tags if x['name']==name),None)
if not match:raise SystemExit('Model tag not installed. Use an exact /api/tags name.')
with urllib.request.urlopen(url+'/api/version',timeout=10) as r: version=json.load(r)
p=Path(__file__).resolve().parents[1]/'Model_Prompts_Config/actual_model_manifest.json'
p.write_text(json.dumps({'provider':'Ollama','runtime':version,'model':match},indent=2));print(p)
