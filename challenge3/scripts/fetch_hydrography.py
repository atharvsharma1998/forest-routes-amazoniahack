"""Inspect ANA's discovered public stream services; cache metadata locally."""
import json
from pathlib import Path
import urllib.request, urllib.parse
out=Path(__file__).resolve().parents[1]/'private/hydrography'
out.mkdir(parents=True,exist_ok=True)
for name,service in [('courses','SNIRH2016/Cursos_dAgua/MapServer'),('watercourse','DADOSABERTOS/Curso_dÁgua/MapServer')]:
    url='https://www.snirh.gov.br/arcgis/rest/services/'+urllib.parse.quote(service,safe='/')+'?f=pjson'
    try:
        with urllib.request.urlopen(url,timeout=25) as r: data=json.load(r)
        (out/(name+'-service.json')).write_text(json.dumps(data))
        print(name,'layers',data.get('layers',[]),'error',data.get('error'),flush=True)
    except Exception as e: print(name,str(e),flush=True)

service='https://www.snirh.gov.br/arcgis/rest/services/SNIRH2016/Cursos_dAgua/MapServer/0'
def get(params, suffix=''):
    url=service+suffix+'?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=35) as r: data=json.load(r)
    if 'error' in data: raise RuntimeError(data['error'])
    return data
try:
    metadata=get({'f':'pjson'})
    (out/'river-layer-metadata.json').write_text(json.dumps(metadata))
    ids=get({'f':'json','where':'1=1','geometry':'-48.5,-3.9,-46.5,-2.2',
             'geometryType':'esriGeometryEnvelope','inSR':4326,
             'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'},'/query')
    objects=ids.get('objectIds') or []
    print('Municipal-region river features:',len(objects),flush=True)
    features=[]
    for start in range(0,len(objects),500):
        block=get({'f':'json','objectIds':','.join(map(str,objects[start:start+500])),
                   'outFields':ids['objectIdFieldName'],'returnGeometry':'true','outSR':4326},'/query')
        for feature in block['features']:
            paths=(feature.get('geometry') or {}).get('paths')
            if not paths:
                raise RuntimeError('ANA returned a feature without geometry')
            geometry={'type':'MultiLineString','coordinates':[[c[:2] for c in path] for path in paths]}
            features.append({'type':'Feature','geometry':geometry,'properties':feature['attributes'],
                             'id':feature['attributes'][ids['objectIdFieldName']]})
    if len(features)!=len(objects): raise RuntimeError('Incomplete hydrography response')
    (out/'rivers.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
    (out/'manifest.json').write_text(json.dumps({'source_url':service,'downloaded_on':'2026-09-12',
        'queried_region':'coarse Paragominas surrounding bounding box', 'feature_count':len(features),
        'limitation':'Centerlines are screening evidence; absence does not prove no water, intersection does not prove no bridge.'},indent=2))
    print('Saved complete river extract',len(features),flush=True)
except Exception as error:
    print('River extract failed:',type(error).__name__,str(error),flush=True)
    (out/'manifest.json').write_text(json.dumps({'status':'failed','reason':str(error),'usable_river_geometries':0},indent=2))
    raise SystemExit(1)
