"""Plot downloaded imagery and input-road overlays locally, without services."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from shapely.geometry import shape, box
from shapely.ops import transform
from shapely.strtree import STRtree
from forest_routes.core import load_roads, PROJECT

root=Path(__file__).resolve().parents[2]
private=root/'challenge3/private'
records=json.loads((private/'imagery/review-imagery.json').read_text())
gaps={f['properties']['gap_id']:f for f in json.loads((private/'outputs/junction_review.geojson').read_text())['features']}
roads,_=load_roads(root/'Incubation material/Challenge 3')
tree=STRtree([r.geometry for r in roads])
for page in range(4):
    fig,axes=plt.subplots(2,2,figsize=(11,10),layout='constrained')
    for row,record in enumerate(records[2*page:2*page+2]):
        g=transform(PROJECT.transform,shape(gaps[record['gap_id']]['geometry']))
        cx,cy=g.centroid.coords[0]
        bounds=record['bounds_utm23s']; extent=[bounds[0],bounds[2],bounds[1],bounds[3]]
        raster=Image.open(private/'imagery'/record['file'])
        nearby=tree.query(box(cx-350,cy-350,cx+350,cy+350))
        for col in range(2):
            ax=axes[row,col]
            ax.imshow(raster,extent=extent,interpolation='nearest')
            ax.set_xlim(cx-300,cx+300);ax.set_ylim(cy-300,cy+300)
            ax.set_xticks([]);ax.set_yticks([])
            if col:
                for i in nearby:
                    r=roads[i]; x,y=r.geometry.xy
                    ax.plot(x,y,color='#6ee7e5' if r.source=='osm' else '#ffe568',lw=1.3,alpha=.9)
                ax.plot(*g.xy,color='#ff334e',lw=3,marker='o',markersize=4)
            else:
                ax.plot(cx,cy,'+',color='white',ms=10,mew=1)
            ax.plot([cx-260,cx-160],[cy-255,cy-255],color='white',lw=3)
            ax.text(cx-260,cy-242,'100 m',color='white',fontsize=9,backgroundcolor='#00000077')
            ax.set_title(('Original image' if col==0 else 'OSM cyan / PrevisIA yellow / gap red')+'\n'+record['gap_id']+' · '+str(gaps[record['gap_id']]['properties']['length_m'])+' m',fontsize=10)
    fig.suptitle('PRIVATE · Junction evidence · Sentinel-2, 3 September 2026\nNative 10 m pixels; no bridge or vehicle-passability certification',fontsize=13)
    fig.savefig(private/'imagery'/f'review-page-{page+1}.png',dpi=130)
    plt.close(fig)
print('Rendered four private review sheets')
