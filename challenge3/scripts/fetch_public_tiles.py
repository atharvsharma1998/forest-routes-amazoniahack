"""Download whole public granules from the existing coarse-region catalog.

This acquisition script never reads challenge pairs, road geometries, route
outputs, or review coordinates. All outgoing URLs are public catalog asset URLs.
Private corridor cropping is a separate, entirely local operation.
"""
import json,urllib.request,urllib.parse,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
P=Path(__file__).resolve().parents[1]/'private';OUT=P/'satellite_tiles';OUT.mkdir(exist_ok=True)
scenes=json.loads((P/'imagery/sentinel-scenes.json').read_text())['features']
date=max(s['properties']['datetime'] for s in scenes)
selected=[s for s in scenes if s['properties']['datetime']==date]
def download(s):
 target=OUT/(s['id']+'.tif')
 try:
  if not target.exists():
   url='https://planetarycomputer.microsoft.com/api/sas/v1/sign?'+urllib.parse.urlencode({'href':s['assets']['visual']['href']})
   with urllib.request.urlopen(url,timeout=40) as f:signed=json.load(f)['href']
   temp=target.with_suffix('.part')
   with urllib.request.urlopen(signed,timeout=90) as f,temp.open('wb') as out:shutil.copyfileobj(f,out)
   temp.replace(target)
  print('Whole public tile',s['properties']['s2:mgrs_tile'],target.stat().st_size,'bytes',flush=True)
  return {'id':s['id'],'file':target.name,'date':date,'epsg':s['properties']['proj:epsg'],'transform':s['assets']['visual']['proj:transform'],'status':'downloaded','bytes':target.stat().st_size}
 except Exception as e:return {'id':s['id'],'status':'failed','error':type(e).__name__}
with ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(download,selected))
(OUT/'manifest.json').write_text(json.dumps({'method':'whole public catalog tiles; no private-coordinate requests','tiles':records},indent=2))
print('Public tiles downloaded',sum(r['status']=='downloaded' for r in records),'/',len(records),flush=True)
