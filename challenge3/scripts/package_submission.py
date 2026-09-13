"""Allowlisted public source release. Never recursively copy the workspace."""
import json,zipfile,hashlib,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];out=P/'public/dist'
results={}
for key,folder in [('exploratory','outputs'),('quarantine','quarantine'),('screened','reviewed')]:
 d=json.loads((P/'private'/folder/'summary.json').read_text())
 results[key]={'summaries':d['summaries'],'run_seconds':d['run_seconds'],'peak_rss_mb_linux':d['peak_rss_mb_linux'],'rejected_gap_count':len(d['rejected_gap_ids']),'withheld_unscreened_gap_count':d.get('withheld_unscreened_gap_count',0)}
results['river_screening']={k:json.loads((P/'private/reviewed/river_screening.json').read_text())[k] for k in ['route_centerline_intersections','by_pair','by_route_kind','source','limitations']}
results['terrain_screening']=json.loads((P/'private/reviewed/terrain_screening.json').read_text())
portable=json.loads((P/'private/reviewed/portable-validation.json').read_text());results['portable']={k:v for k,v in portable.items() if k!='queries'}
results['field_verified_pairs']=0
(out/'results.json').write_text(json.dumps(results,indent=2))
# Canonical public docs live in public/dist; keep them in sync from repo root copies when present
if (P/'README.md').exists():
 shutil.copy(P/'README.md', out/'README.md')
if (out/'submission.md').exists() is False and (P/'SUBMISSION.md').exists():
 shutil.copy(P/'SUBMISSION.md', out/'submission.md')
files={}
for f in (P/'src/forest_routes').iterdir():
 if f.suffix in ['.py','.js','.html']:files['src/forest_routes/'+f.name]=f
for f in (P/'tests').iterdir():
 if f.suffix in ['.py','.js']:files['tests/'+f.name]=f
for name in ['acquire_environment.py','fetch_environment_assets.py','screen_rivers.py','screen_terrain.py','build_satellite_overview.py','package_submission.py']:
 path=P/'scripts'/name
 if path.exists():files['scripts/'+name]=path
for name in ['gap-review-ledger.json','quarantined-gap-ids.json','screened-candidate-gap-ids.json']:
 files['evidence/'+name]=P/'evidence'/name
for name in ['sample-field-track.gpx','feedback-record.json','accepted-roads.geojson']:
 path=P/'examples'/name
 if path.exists():files['examples/'+name]=path
for name in ['README.md','submission.md','results.json']:files[name]=out/name
files['requirements.txt']=P/'requirements.txt'
if (P/'SUBMISSION.md').exists():files['SUBMISSION.md']=P/'SUBMISSION.md'
zip_path=out/'forest-routes-source.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for name,f in sorted(files.items()):z.write(f,name)
manifest={'files':list(sorted(files)),'archive_bytes':zip_path.stat().st_size,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),
 'exclusions':['participant inputs','real coordinates and routes','real imagery','municipal compact graph','credentials','private file trees','public synthetic demo'],
 'synthetic_files':['examples/*'],
 'dashboards':['private field officer review (report.html)','private map visualization (offline-router.html)']}
(P/'private/public-release-audit.json').write_text(json.dumps(manifest,indent=2))
print('Allowlisted public archive:',len(files),'files,',zip_path.stat().st_size,'bytes')
