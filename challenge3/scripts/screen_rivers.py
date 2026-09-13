"""Flag intersections with ANA stream centerlines; do not infer bridge absence."""
from collections import Counter
import json
import argparse
from pathlib import Path
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform
from shapely.strtree import STRtree
from forest_routes.core import PROJECT, UNPROJECT, key

root=Path(__file__).resolve().parents[1]/'private'
if not (root/'hydrography/rivers.geojson').exists():
    raise SystemExit('No validated river extract. Read private/hydrography/manifest.json and obtain valid line geometries first.')
parser=argparse.ArgumentParser();parser.add_argument('--routes-dir',type=Path,default=root/'outputs');args=parser.parse_args();output=args.routes_dir
features=json.loads((root/'hydrography/rivers.geojson').read_text())['features']
if any(not f.get('geometry') for f in features):
    raise SystemExit('River extract contains missing geometries; screening aborted.')
rivers=[transform(PROJECT.transform,shape(f['geometry'])) for f in features]
tree=STRtree(rivers)
routes=json.loads((output/'routes.geojson').read_text())['features']
checks=[];seen=set();counts=Counter();kind_counts=Counter()
for feature in routes:
    p=feature['properties'];geom=transform(PROJECT.transform,shape(feature['geometry']))
    for i in tree.query(geom,predicate='intersects'):
        intersection=geom.intersection(rivers[i])
        parts=list(intersection.geoms) if hasattr(intersection,'geoms') else [intersection]
        for part in parts:
            if part.is_empty: continue
            point=part if isinstance(part,Point) else part.representative_point()
            dedup=(p['pair_id'],p['kind'],int(i),tuple(round(v,1) for v in point.coords[0]))
            if dedup in seen: continue
            seen.add(dedup);counts[p['pair_id']]+=1;kind_counts[p['kind']]+=1
            checks.append({'type':'Feature','geometry':mapping(transform(UNPROJECT.transform,point)),
                'properties':{'pair_id':p['pair_id'],'route_kind':p['kind'],'gap_id':p['gap_id'],
                 'ana_feature_id':features[i].get('id',i),'intersection_type':part.geom_type,
                 'status':'crossing_requires_evidence','bridge_present':None,
                 'warning':'Centerline intersection only; this does not establish that a bridge is missing.'}})
(output/'river_crossings.geojson').write_text(json.dumps({'type':'FeatureCollection','features':checks}))
summary={'route_centerline_intersections':len(checks),'by_pair':dict(counts),'by_route_kind':dict(kind_counts),
 'source':json.loads((root/'hydrography/manifest.json').read_text())['source_url'],'source_acquisition_date':'not established from service metadata',
 'river_features_downloaded':len(features),'field_verified':False,
 'limitations':['Screening only; no routing edges were rejected from this evidence alone.',
 'Intersections may be valid bridges; no intersection does not prove absence of a water obstacle.',
 'Exact intersections on approximate centerlines; no positional uncertainty buffer applied.']}
(output/'river_screening.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
