"""Local GPX proposal -> explicit review -> export loop; never auto-publish tracks."""
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET

def now():return datetime.now(timezone.utc).isoformat()
def import_gpx(path,synthetic=False):
    payload=Path(path).read_bytes()
    if len(payload)>10_000_000:raise ValueError('GPX exceeds 10 MB limit')
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():raise ValueError('External/declared XML entities are not accepted')
    root=ET.fromstring(payload);features=[];count=0
    for segment in root.findall('.//{*}trkseg'):
        coords=[];times=[];hdop=[]
        for p in segment.findall('{*}trkpt'):
            lon,lat=float(p.attrib['lon']),float(p.attrib['lat'])
            if not math.isfinite(lon+lat) or not -180<=lon<=180 or not -90<=lat<=90:raise ValueError('Invalid coordinates')
            coords.append([lon,lat]);times.append(p.findtext('{*}time'));h=p.findtext('{*}hdop');hdop.append(float(h) if h is not None else None);count+=1
        if len(coords)>=2:features.append({'type':'Feature','properties':{'times':times,'hdop':hdop},'geometry':{'type':'LineString','coordinates':coords}})
    if not features or count>50000:raise ValueError('Need track segments with 2+ points and at most 50000 points')
    digest=hashlib.sha256(payload).hexdigest()
    return {'id':'gpx-'+digest[:16],'sha256':digest,'synthetic':synthetic,'status':'proposed','features':features,
            'history':[{'event':'imported','at':now()}],
            'limitations':['One traversal is not year-round passability or permission to access land.','Coordinates stay local; no automatic shared-map publication.']}

def review(record,decision,reviewer,note):
    if decision not in ['accepted','rejected']:raise ValueError('Decision must be accepted or rejected')
    if not reviewer.strip() or not note.strip():raise ValueError('Named reviewer and evidence note required')
    record=json.loads(json.dumps(record));record['status']=decision
    record['history'].append({'event':'review','decision':decision,'reviewer':reviewer,'note':note,'at':now()})
    return record

def accepted_roads(records):
    features=[]
    for record in records:
        if record['status']!='accepted':continue
        if not any(h.get('decision')=='accepted' for h in record['history']):raise ValueError('Missing acceptance history')
        for i,f in enumerate(record['features']):
            features.append({**f,'properties':{**f['properties'],'record_id':record['id'],'segment':i,'decision':'accepted',
                    'synthetic':record['synthetic'],'sha256':record['sha256'],'review_history':record['history'],
                    'field_verified_for_current_conditions':False}})
    return {'type':'FeatureCollection','features':features}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('import');x.add_argument('gpx',type=Path);x.add_argument('output',type=Path);x.add_argument('--synthetic',action='store_true')
    x=sub.add_parser('review');x.add_argument('record',type=Path);x.add_argument('--decision',choices=['accepted','rejected'],required=True);x.add_argument('--reviewer',required=True);x.add_argument('--note',required=True)
    x=sub.add_parser('export');x.add_argument('output',type=Path);x.add_argument('records',nargs='+',type=Path)
    a=p.parse_args()
    if a.command=='import':value=import_gpx(a.gpx,a.synthetic);path=a.output
    elif a.command=='review':value=review(json.loads(a.record.read_text()),a.decision,a.reviewer,a.note);path=a.record
    else:value=accepted_roads([json.loads(f.read_text()) for f in a.records]);path=a.output
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(path)
    print('Saved',path)
if __name__=='__main__':main()
