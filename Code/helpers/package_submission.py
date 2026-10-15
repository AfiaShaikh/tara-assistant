"""Build an archive and SHA-256 manifest without virtualenv, secrets or runtime DBs."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[2]
skip={'.venv','.venv-wsl','__pycache__','.pytest_cache','runtime','.git','demo_frames','node_modules'}
files=[p for p in sorted(root.rglob('*')) if p.is_file() and not set(p.relative_to(root).parts)&skip and p.name not in {'.env','SUBMISSION_MANIFEST.json'} and p.suffix not in {'.pyc','.db','.zip'}]
manifest={'root_folder':root.name,'files':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
m=root/'SUBMISSION_MANIFEST.json';m.write_text(json.dumps(manifest,indent=2));files.append(m)
out=root.parent/(root.name+'.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(root.parent))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for record in manifest['files']:
        assert hashlib.sha256(z.read(root.name+'/'+record['path'])).hexdigest()==record['sha256']
print(json.dumps({'archive':str(out),'files':len(files),'bytes':out.stat().st_size,'verified':True}))
