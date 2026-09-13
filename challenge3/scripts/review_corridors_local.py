"""Create private corridor contact sheets using already downloaded public tiles only."""
import json, math
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw
from shapely.geometry import shape, LineString
from shapely.ops import transform
from pyproj import Transformer
from forest_routes.core import PROJECT, UNPROJECT
P=Path(__file__).resolve().parents[1]/'private';out=P/'corridor_review';out.mkdir(exist_ok=True)
Image.MAX_IMAGE_PIXELS=150_000_000
meta=json.loads((P/'satellite_tiles/manifest.json').read_text())['tiles'];images={}
groups=defaultdict(list)
for f in json.loads((P/'reviewed/routes.geojson').read_text())['features']:
 g=transform(PROJECT.transform,shape(f['geometry']));groups[f['properties']['pair_id']].extend(list(g.coords) if not groups[f['properties']['pair_id']] else list(g.coords)[1:])
records=[]
for pid,coords in groups.items():
 line=LineString(coords);count=max(1,math.ceil(line.length/4000));panels=[]
 for n in range(count):
  station=(n+.5)*line.length/count;c=line.interpolate(station);chosen=None
  for t in sorted(meta,key=lambda t:t['epsg']!=32723):
   if t['status']!='downloaded':continue
   conv=Transformer.from_crs(32723,t['epsg'],always_xy=True);x,y=conv.transform(c.x,c.y);a,b,x0,d,e,y0=t['transform'];col=(x-x0)/a;row=(y-y0)/e
   if 300<=col<10680 and 300<=row<10680:chosen=(t,conv,col,row);break
  entry={'pair_id':pid,'window_index':n,'station_m':round(station),'route_length_m':round(line.length),'window_width_m':6000,'status':'awaiting_visual_screen'}
  if chosen:
   t,conv,col,row=chosen
   if t['file'] not in images:images[t['file']]=Image.open(P/'satellite_tiles'/t['file'])
   box=(int(col)-300,int(row)-300,int(col)+300,int(row)+300);crop=images[t['file']].crop(box).convert('RGB');over=crop.copy();draw=ImageDraw.Draw(over)
   points=[]
   for xx,yy in coords:
    x,y=conv.transform(xx,yy);points.append(((x-t['transform'][2])/10-box[0],(y-t['transform'][5])/-10-box[1]))
   draw.line(points,fill='#ff4794',width=3);draw.ellipse((294,294,306,306),outline='white',width=2)
   entry['tile_id']=t['id'];entry['date']=t['date']
  else:
   crop=Image.new('RGB',(600,600),'#333333');over=crop.copy();entry['status']='no_full_window_tile'
  panel=Image.new('RGB',(640,350),'white');d=ImageDraw.Draw(panel);d.text((8,5),f'{pid} window {n+1}/{count} | {station/1000:.1f} km | 6 km square',fill='black');panel.paste(crop.resize((320,320)),(0,30));panel.paste(over.resize((320,320)),(320,30));panels.append(panel);records.append(entry)
 for page,start in enumerate(range(0,len(panels),6)):
  sheet=Image.new('RGB',(1280,1050),'white')
  for j,panel in enumerate(panels[start:start+6]):sheet.paste(panel,((j%2)*640,(j//2)*350))
  path=out/f'{pid}-page-{page+1}.jpg';sheet.save(path,quality=90);print(path.name,flush=True)
(out/'coverage.json').write_text(json.dumps({'method':'Local-only crops; overlapping 6 km windows at <=4 km along all candidate routes; original beside pink route overlay','field_verified':False,'windows':records},indent=2))
