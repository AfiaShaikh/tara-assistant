"""Run INSIDE the app environment after a genuine successful generation."""
import argparse,json,sys,os
from pathlib import Path
from datetime import datetime,timezone
from ai_assessment import model_status
from storage import Store
p=argparse.ArgumentParser();p.add_argument('--require-postgres',action='store_true');p.add_argument('--output',default=str(Path(__file__).resolve().parents[1]/'Evaluation_Results/ai_deployment_verification.json'));args=p.parse_args()
s=Store(os.getenv("TARA_DB",str(Path(__file__).resolve().parent/"runtime/tara.db")));health=model_status();records=s.list_assessments();success=[r for r in records if r.get('output') and r['status'] in ('Draft','Reviewed','Rejected')]
evidence={'verified_at':datetime.now(timezone.utc).isoformat(),'postgres_active':s.pg,'model_status':health,'successful_assessment_count':len(success),'assessments':[{'id':r['id'],'title':r['title'],'model':r['model'],'status':r['status'],'assets':len(r['output']['assets']),'threats':len(r['output']['threats']),'citation_ids_valid':all(set(x['evidence_ids'])<={e['id'] for e in r['evidence']} for x in r['output']['assets']+r['output']['threats'])} for r in success],'expert_quality_review':'Not established by this script'}
evidence['deployment_check_passed']=health['ready'] and bool(success) and (s.pg or not args.require_postgres)
Path(args.output).write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2));sys.exit(0 if evidence['deployment_check_passed'] else 1)
