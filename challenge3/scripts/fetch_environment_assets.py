"""Acquire complete public ANA geometry and numeric Copernicus DSM grids."""
import json,urllib.request,urllib.parse,hashlib,io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
P=Path(__file__).resolve().parents[1]/'private';OUT=P/'evidence'
def get(url,params):
 with urllib.request.urlopen(url+'?'+urllib.parse.urlencode(params),timeout=50) as r:return json.load(r)
def hydro():
 for service in ['https://www.snirh.gov.br/arcgis/rest/services/SNIRH2016/Cursos_Agua_dominialidade/MapServer/0','https://www.snirh.gov.br/arcgis/rest/services/INDE/Camadas/MapServer/58']:
  try:
   ids=get(service+'/query',{'f':'json','where':'1=1','geometry':'-48.5,-3.9,-46.5,-2.2','geometryType':'esriGeometryEnvelope','inSR':4326,'returnIdsOnly':'true'})
   objects=ids.get('objectIds') or [];print('ANA IDs',len(objects),flush=True)
   if not objects:continue
   features=[]
   for start in range(0,len(objects),400):
    data=get(service+'/query',{'f':'json','objectIds':','.join(map(str,objects[start:start+400])),'outFields':'*','outSR':4326,'returnGeometry':'true'})
    for f in data.get('features',[]):
     paths=(f.get('geometry') or {}).get('paths')
     if not paths:raise ValueError('Geometry missing')
     features.append({'type':'Feature','id':f['attributes'][ids['objectIdFieldName']], 'properties':f['attributes'],'geometry':{'type':'MultiLineString','coordinates':[[c[:2] for c in line] for line in paths]}})
   if len(features)!=len(objects):raise ValueError('Incomplete feature count')
   target=P/'hydrography/rivers.geojson';target.write_text(json.dumps({'type':'FeatureCollection','features':features}))
   (P/'hydrography/manifest.json').write_text(json.dumps({'status':'complete','source_url':service,'downloaded_on':'2026-09-13','feature_count':len(features),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'limitation':'Screening centerlines only; bridge presence and positional accuracy unverified.'},indent=2))
   print('ANA geometry complete',len(features),flush=True);return
  except Exception as e:print('ANA attempt',str(e),flush=True)
 print('ANA acquisition incomplete',flush=True)
def dem(scene):
 name=scene['id'];path=OUT/(name+'.npy')
 bounds=scene['bbox'];params={'collection':'cop-dem-glo-30','item':name,'assets':'data','return_mask':'true','resampling':'nearest'}
 url='https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/'+','.join(map(str,bounds))+'/3600x3600.npy?'+urllib.parse.urlencode(params)
 try:
  if not path.exists():
   with urllib.request.urlopen(url,timeout=90) as r:payload=r.read()
   a=np.load(io.BytesIO(payload),allow_pickle=False);np.save(path,a)
  a=np.load(path,mmap_mode='r');print('DEM',name,a.shape,a.dtype,flush=True)
  return {'id':name,'file':path.name,'bbox':bounds,'shape':list(a.shape),'url':url,'native_sampling_m':30,'model':'Digital surface model; canopy/buildings may influence slope','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 except Exception as e:print('DEM error',name,str(e),flush=True);return {'id':name,'error':str(e)}
scenes=json.loads((OUT/'dem-scenes.json').read_text())['features']
with ThreadPoolExecutor(max_workers=4) as pool:
 river=pool.submit(hydro);dems=list(pool.map(dem,scenes));river.result()
(OUT/'dem-manifest.json').write_text(json.dumps({'source':'Copernicus DEM GLO-30 via Microsoft Planetary Computer','acquired_on':'2026-09-13','tiles':dems},indent=2))
