"""Generate a wholly synthetic public demo with the real portable router."""
import json,shutil
from pathlib import Path
from shapely.geometry import LineString
from forest_routes.core import Road,Network
from forest_routes.portable import export_graph
from forest_routes.feedback import import_gpx,review,accepted_roads
P=Path(__file__).resolve().parents[1];out=P/'public/dist';out.mkdir(exist_ok=True)
roads=[Road(LineString(c),'osm','synthetic-'+str(i)) for i,c in enumerate([
[(0,0),(1800,0)],[(1800,0),(4000,0)],[(1800,0),(1800,1200),(3500,1200)],
[(4000,0),(4000,1200)],[(4700,0),(6500,0)],[(6500,0),(8000,0)],[(6500,0),(6500,1500)]])]
pairs=[{'id':'Western visit','origin':[0,20],'destination':[3500,1400]},
       {'id':'Eastern visit','origin':[0,20],'destination':[7400,220]},
       {'id':'Long final walk','origin':[0,20],'destination':[8000,1100]}]
tmp=P/'private/synthetic';tmp.mkdir(exist_ok=True)
before=export_graph(Network(roads),tmp,pairs,set(),150,synthetic=True)
coords=[(4000,0),(4350,0),(4700,0)]
gpx='<gpx version="1.1" creator="Forest Routes synthetic fixture"><trk><name>SIMULATED field update</name><trkseg>'+''.join(f'<trkpt lat="{y/111319.49:.12f}" lon="{x/111319.49:.12f}"><time>2026-09-01T12:0{i}:00Z</time><hdop>1.0</hdop></trkpt>' for i,(x,y) in enumerate(coords))+'</trkseg></trk></gpx>'
(tmp/'sample-field-track.gpx').write_text(gpx)
proposal=import_gpx(tmp/'sample-field-track.gpx',synthetic=True)
record=review(proposal,'accepted','Simulated reviewer','Synthetic known connection accepted for demonstration only; not real field evidence')
accepted=accepted_roads([record])
for f in accepted['features']:
 local=[[round(x*111319.49,1),round(y*111319.49,1)] for x,y in f['geometry']['coordinates']]
 roads.append(Road(LineString(local),'field_gps',record['id']))
after=export_graph(Network(roads),tmp,pairs,set(),150,synthetic=True)
(out/'demo-data.js').write_text('window.DEMO_DATA='+json.dumps({'before':before,'after':after},separators=(',',':'))+';')
shutil.copy(P/'src/forest_routes/router.js',out/'router.js')
(tmp/'feedback-record.json').write_text(json.dumps(record,indent=2))
(tmp/'accepted-roads.geojson').write_text(json.dumps(accepted,indent=2))
print('Synthetic demo created; no supplied geometry used')
