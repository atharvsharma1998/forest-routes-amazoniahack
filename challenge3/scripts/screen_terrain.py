"""Continuous route sampling of Copernicus DSM; surface grade is not road grade."""
import argparse,json
from pathlib import Path
from collections import defaultdict
import numpy as np
from shapely.geometry import shape,LineString
from shapely.ops import transform
from forest_routes.core import PROJECT,UNPROJECT
P=Path(__file__).resolve().parents[1]/'private'
parser=argparse.ArgumentParser();parser.add_argument('--routes-dir',type=Path,default=P/'outputs');args=parser.parse_args()
manifest=json.loads((P/'evidence/dem-manifest.json').read_text());tiles=[]
for t in manifest['tiles']:
 if 'file' in t:tiles.append((t,np.load(P/'evidence'/t['file'],mmap_mode='r')))
def sample(x,y):
 lon,lat=UNPROJECT.transform(x,y)
 for tile,a in tiles:
  x0,y0,x1,y1=tile['bbox']
  if x0<=lon<x1 and y0<=lat<y1:
   row=min(a.shape[1]-1,int((y1-lat)/(y1-y0)*a.shape[1]));col=min(a.shape[2]-1,int((lon-x0)/(x1-x0)*a.shape[2]))
   z=float(a[0,row,col]);mask=float(a[1,row,col])
   return z if mask>0 and np.isfinite(z) and -500<z<9000 else None
 return None
features=json.loads((args.routes_dir/'routes.geojson').read_text())['features'];groups=defaultdict(list)
for f in features:groups[f['properties']['pair_id']].append(transform(PROJECT.transform,shape(f['geometry'])))
rows=[]
for pid,geometries in groups.items():
 coords=[]
 for g in geometries:coords.extend(list(g.coords) if not coords else list(g.coords)[1:])
 route=LineString(coords);positions=np.linspace(0,route.length,max(2,int(np.ceil(route.length/100))+1));z=[sample(*route.interpolate(float(s)).coords[0]) for s in positions]
 grades=[abs(b-a)/(positions[i+1]-positions[i])*100 for i,(a,b) in enumerate(zip(z,z[1:])) if a is not None and b is not None]
 values=[v for v in z if v is not None]
 rows.append({'pair_id':pid,'sample_count':len(z),'valid_samples':len(values),'coverage_fraction':len(values)/len(z),
 'sampling_interval_m':float(positions[1]-positions[0]),'elevation_min_m':min(values) if values else None,'elevation_max_m':max(values) if values else None,
 'surface_grade_p95_pct':float(np.percentile(grades,95)) if grades else None,'surface_grade_max_pct':max(grades) if grades else None,
 'surface_grade_intervals_above_15pct':int(sum(g>15 for g in grades)),
 'interpretation':'DSM surface-change screening; canopy, bridges and terrain resolution prevent interpreting this as measured road gradient.'})
(args.routes_dir/'terrain_screening.json').write_text(json.dumps({'source':'Copernicus DEM GLO-30','native_sampling_m':30,'rows':rows,'model':'surface, not bare earth','field_verified':False},indent=2))
print('Terrain screening:',len(rows),'routes,',sum(r['valid_samples'] for r in rows),'valid samples of',sum(r['sample_count'] for r in rows))
