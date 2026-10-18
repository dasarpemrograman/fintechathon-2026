"""Retain bounded real search/retrieval evidence for explicit illustrative goods."""
import argparse,hashlib,json,sys,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.adapters.network import fetch
from packages.adapters.providers import search,fx_rates
from scripts.probe_live_sources import Text
from services.api.store import DomainError
from pypdf import PdfReader

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',default='config/live-acceptance-scopes-v1.json')
parser.add_argument('--retry-from')
parser.add_argument('--workers',type=int,choices=[1,2,3],default=3)
args=parser.parse_args()
manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
root=Path('.local/acceptance-source-receipts');root.mkdir(parents=True,exist_ok=True,mode=0o700)
report={'manifest_version':manifest['version'],'retrieved_at':datetime.now(timezone.utc).isoformat(),'scope_status':manifest['scope_status'],'lanes':manifest['lanes'],'limits':{'search_queries':9,'source_pages':18,'high_level_actions':30},'searches':[],'sources':[],'fx':[],'coverage_acceptance':False}
previous=json.loads(Path(args.retry_from).read_text(encoding='utf-8')) if args.retry_from else None
if previous:
 assert previous['manifest_version']==manifest['version']
 report['searches']=previous['searches'];report['fx']=previous['fx']
 report['limits']['search_queries']=0;report['limits']['high_level_actions']=18
 report['retained_prior_receipts']=args.retry_from
for lane in ([] if previous else manifest['lanes']):
 for cat,domain in [('official_export',lane['export_domain']),('official_import',lane['import_domain']),('finance',lane['finance_domain'])]:
  query=lane['search_terms']+' '+lane['origin']+' '+lane['destination']+' '+cat.replace('_',' ')+' site:'+domain
  row={'lane':lane['id'],'category':cat,'query':query}
  try:
   v=search(query,2);row.update(status='passed',receipt={k:v for k,v in v.items() if k!='data'},candidates=v['data'])
  except DomainError as e:row.update(status='blocked',code=e.code)
  report['searches'].append(row)
def retrieve(source):
 row={**source,'retrieved_at':datetime.now(timezone.utc).isoformat()}
 try:
  v=fetch(source['url']);raw=v['content'];h=hashlib.sha256(raw).hexdigest();(root/(h+'.source')).write_bytes(raw)
  row['receipt']={k:v for k,v in v.items() if k!='content'};row['content_hash']=h;row['bytes']=len(raw)
  if v['media_type']=='application/pdf':
   pdf=PdfReader(BytesIO(raw));assert len(pdf.pages)<=100;text='\n'.join(page.extract_text() or '' for page in pdf.pages)[:200000];row['locator']='PDF page text'
  elif v['media_type'] in {'text/html','text/plain'}:
   p=Text();p.feed(raw.decode('utf-8',errors='replace'));text=' '.join(p.words)[:200000];row['title']=' '.join(p.titles)[:250];row['locator']='HTML text'
  else:raise ValueError('Unsupported source type')
  row['matched_terms']=[t for t in source['terms'] if t.casefold() in text.casefold()]
  row['status']='retrieved_and_parsed' if len(row['matched_terms'])==len(source['terms']) else 'retrieved_requires_review'
  row['source_is_executable_quote']=False;row['review_scope']='assessment limited to illustrative product and stated exclusions'
  (root/(h+'.txt')).write_text(text,encoding='utf-8')
 except DomainError as e:row.update(status='blocked',code=e.code,reason=e.reason)
 except Exception as e:row.update(status='parse_failed',error_type=type(e).__name__)
 print(json.dumps({'source':source['id'],'status':row['status']}),flush=True)
 return row
retained={s['id']:s for s in previous['sources'] if s['status']=='retrieved_and_parsed'} if previous else {}
with ThreadPoolExecutor(max_workers=args.workers) as pool:
 retried={r['id']:r for r in pool.map(retrieve,[s for s in manifest['sources'] if s['id'] not in retained])}
report['sources']=[retained.get(s['id']) or retried[s['id']] for s in manifest['sources']]
for lane in ([] if previous else manifest['lanes']):
 try:
  v=fx_rates(*([lane['currency_pair'][0],[lane['currency_pair'][1]]]))
  report['fx'].append({'lane':lane['id'],'status':'passed','result':v})
 except DomainError as e:report['fx'].append({'lane':lane['id'],'status':'blocked','code':e.code})
report['retrieval_gate_passed']=all(r['status']=='passed' for r in report['searches']) and all(r['status']=='retrieved_and_parsed' for r in report['sources']) and all(r['status']=='passed' for r in report['fx'])
report['limitations']=['The manifest describes operator-selected test goods, not a customer shipment.','Public access and matching text are retrieval evidence; each assessment states applicability and exclusions.','No executable quote, lender approval, blanket legal clearance or national tariff rate is inferred.','Final acceptance is reviewed separately with the configured model receipt and remaining source limitations.']
Path('.local/acceptance-source-probes.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'retrieval_gate_passed':report['retrieval_gate_passed'],'search_passed':sum(r['status']=='passed' for r in report['searches']),'sources_parsed':sum(r['status']=='retrieved_and_parsed' for r in report['sources']),'fx_passed':sum(r['status']=='passed' for r in report['fx'])}),flush=True)
raise SystemExit(0 if report['retrieval_gate_passed'] else 2)
