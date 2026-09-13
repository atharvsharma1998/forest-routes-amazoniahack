"""Fetch public hydrography diagnostics and DEM catalog; no participant data upload."""
import json,urllib.request,urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT=Path(__file__).resolve().parents[1]/'private/evidence';OUT.mkdir(exist_ok=True)
def get(url,params):
 with urllib.request.urlopen(url+'?'+urllib.parse.urlencode(params),timeout=40) as f: return json.load(f)
def run(item):
 name,url,params=item
 try:
  d=get(url,params);(OUT/(name+'.json')).write_text(json.dumps(d)); print(name,'features',len(d.get('features',[])),'error',d.get('error'),flush=True)
  if d.get('features'):
   f=d['features'][0];print(name,'geometry',list((f.get('geometry') or {})),flush=True)
 except Exception as e: print(name,str(e),flush=True)
q={'f':'json','where':'1=1','geometry':'-48.5,-3.9,-46.5,-2.2','geometryType':'esriGeometryEnvelope','inSR':4326,'outSR':4326,'returnGeometry':'true','outFields':'*'}
items=[('ana-native','https://www.snirh.gov.br/arcgis/rest/services/SNIRH2016/Cursos_dAgua/MapServer/0/query',q),
('ana-alternative','https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/Curso_d%C3%81gua/MapServer/0/query',q),
('ana-drainage','https://portal1.snirh.gov.br/arcgis/rest/services/IG/Servicos_Base_IG/FeatureServer/1/query',{**q,'resultRecordCount':1000}),
('dem-scenes','https://planetarycomputer.microsoft.com/api/stac/v1/search',{'collections':'cop-dem-glo-30','bbox':'-48.5,-3.9,-46.5,-2.2','limit':100})]
with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(run,items))
