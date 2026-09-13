"""Record screening decisions without converting them into field approval."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'private'
notes=json.loads((P/'imagery/visual-review.json').read_text())
features=json.loads((P/'outputs/junction_review.geojson').read_text())['features']
quarantine=[];retained=[];ledger=[]
for note in notes:
 decision='retain_as_unverified_candidate' if note['screening_status']=='corridor_plausible' else 'quarantine_pending_evidence'
 (retained if decision.startswith('retain') else quarantine).append(note['gap_id'])
 ledger.append({**note,'decision':decision,'review_status':'screened','reviewed_on':'2026-09-13',
 'decision_basis':'Dated imagery screening only; precautionary exclusion does not assert road absence.'})
by_id={r['gap_id']:r for r in ledger}
for f in features:
 r=by_id[f['properties']['gap_id']]
 f['properties'].update(review_status=r['decision'],evidence={'scene_id':r['scene_id'],'note':r['note'],'screening_status':r['screening_status']},field_verified=False)
(P/'evidence/gap-review-ledger.json').write_text(json.dumps(ledger,indent=2))
(P/'evidence/quarantined-gap-ids.json').write_text(json.dumps(quarantine,indent=2))
(P/'evidence/screened-candidate-gap-ids.json').write_text(json.dumps(retained,indent=2))
(P/'outputs/junction_review.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
print('Screened',len(ledger),'quarantined',len(quarantine),'retained unverified',len(retained))
