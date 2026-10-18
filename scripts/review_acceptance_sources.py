"""Review the declared test scope against retained, hashed live source bodies."""
import json,re,hashlib
from pathlib import Path
from datetime import datetime,timezone

root=Path('.local/acceptance-source-receipts')
report=json.loads(Path('.local/acceptance-source-probes.json').read_text(encoding='utf-8'))
assert report['retrieval_gate_passed']
assert len(report['searches'])==9 and len(report['sources'])==18 and len(report['fx'])==3
by_id={r['id']:r for r in report['sources']}
text={}
for row in report['sources']:
 assert row['status']=='retrieved_and_parsed'
 raw=(root/(row['content_hash']+'.source')).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==row['content_hash']
 text[row['id']]=' '.join((root/(row['content_hash']+'.txt')).read_text(encoding='utf-8').split())
def locate(source,pattern):
 match=re.search(pattern,text[source],re.I)
 assert match,(source,pattern)
 return {'source_id':source,'url':by_id[source]['url'],'content_hash':by_id[source]['content_hash'],'normalized_text_span':[match.start(),match.end()]},match

coffee_ref,m=locate('coffee-market',r'15-Oct\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)')
assert m.group(1)=='260.37'
pcb_ref,m=locate('pcb-market',r'From\s*\$\s*(\d+\.\d+)\s*/\s*(\d+)\s*pcs')
assert m.groups()==('2.00','5')
mango_ref,m=locate('mango-market',r'FOB prices for natural dried mangoes usually range between\s*€\s*(\d+)\s*and\s*€\s*(\d+)\s*per kilo')
assert m.groups()==('8','12')
lc_ref,m=locate('cn-finance',r'up to\s*(\d+)%\s*of the L/C amount')
assert m.group(1)=='80'
id_ref,_=locate('id-finance',r'Rupiah atau valas yang tersedia')
ke_ref,_=locate('ke-finance',r'Pre-shipment financing')
locate('ke-finance',r'Post shipment financing')

observations=[
 {'lane':'ID-SG','kind':'market_indicator','value':'260.37','unit':'US cents/lb','observation_date':'2026-10-15','product_group':'ICO composite indicator','comparable_status':'excluded_as_executable_quote','reasons':['Not a specific Indonesian arabica grade, lot size or Incoterm','The 16 October row is blank; no newer value invented'],'reference':coffee_ref},
 {'lane':'CN-SG','kind':'supplier_public_promotion','amount':'2.00','currency':'USD','quantity':'5','unit':'bare PCBs','comparable_status':'excluded_moq_and_specification_mismatch','reasons':['Promotional prototype tier differs from the declared 1000-board lot','Final dimensions, Gerber design, finish and delivery need a supplier quotation'],'reference':pcb_ref},
 {'lane':'KE-DE','kind':'indicative_market_range','low':'8','high':'12','currency':'EUR','unit':'kg','incoterm':'FOB','comparable_status':'indicative_only','reasons':['Broad natural dried-mango range; not a Kenyan supplier offer or delivered-Germany quote','Retail end-market figures are excluded from exporter pricing'],'reference':mango_ref},
 {'lane':'ID-SG','kind':'finance_fit','product':'Indonesia Eximbank PMKE','draw_stage':'export working capital','currencies':'IDR or available foreign currencies','interest_rate':None,'fees':None,'eligibility':'needs_lender_review','pricing_status':'quote_required','reference':id_ref},
 {'lane':'CN-SG','kind':'finance_fit','product':'ICBC Packing Loan','draw_stage':'pre_shipment','requires_export_lc':True,'maximum_published_lc_fraction':'0.80','fit_without_lc':'incompatible','interest_rate':None,'tenor':None,'eligibility':'approved_credit_line_required','reference':lc_ref},
 {'lane':'KE-DE','kind':'finance_fit','product':'KCB Export Financing','pre_shipment':'confirmed_order_procurement','post_shipment':'invoice_bill_or_lc_discounting','post_shipment_for_pre_shipment_gap':'incompatible','interest_rate':None,'tenor':None,'reference':ke_ref}
]
review={
 'reviewed_at':datetime.now(timezone.utc).isoformat(),
 'manifest_version':report['manifest_version'],
 'scope':report['scope_status'],
 'source_receipt_report_hash':hashlib.sha256(Path('.local/acceptance-source-probes.json').read_bytes()).hexdigest(),
 'source_retrieval_acceptance':True,
 'searches_passed':9,'source_pages_passed':18,'fx_pairs_passed':3,
 'observations':observations,
 'rules_review':[{'source_id':r['id'],'lanes':r['lanes'],'category':r['category'],'assessment':r['assessment'],'source_hash':r['content_hash']} for r in report['sources'] if r['category'] in {'official_export','official_import','official_product_guidance','hs_nomenclature','logistics_reference'}],
 'freshness_review':{'retrieved_on':'2026-10-18','coffee_observation_date':'2026-10-15','coffee_age_days':3,'mango_market_guide':'2026 edition; indicative ranges only','finance_pages':'Retrieved on review date; rate, tenor and borrower eligibility remain unconfirmed','hs_nomenclature':'Six-digit headings only; foreign national tariff rates and national suffixes excluded'},
 'limitations':['This accepts evidence retrieval, normalization and conservative comparisons for the three declared test scopes, not universal commodity/country coverage.','No fetched rule is promoted to a binding clearance decision or a customer-specific verified fact.','No executable freight or goods quote, lender approval, phytosanitary requirement for dried mango, or strategic-goods exemption is invented.','Commercial charges, national classification detail and unresolved shipment predicates remain explicit unknowns.'],
 'configured_model_required_separately':True
}
Path('.local/acceptance-source-review.json').write_text(json.dumps(review,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'source_retrieval_acceptance':True,'structured_market_observations':3,'structured_finance_fit_reviews':3,'scoped_rule_logistics_and_hs_reviews':len(review['rules_review'])}))
