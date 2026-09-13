"""Download public imagery metadata and API schema for a coarse municipal region.

No participant features or site coordinates are uploaded. Endpoint geometries
may later be used locally to select imagery for the review queue.
"""
import json
from pathlib import Path
import urllib.parse
import urllib.request

OUT = Path(__file__).resolve().parents[1] / 'private' / 'imagery'
OUT.mkdir(parents=True, exist_ok=True)
query = urllib.parse.urlencode({'collections': 'sentinel-2-l2a',
    'bbox': '-48.5,-3.9,-46.5,-2.2', 'datetime': '2025-06-01T00:00:00Z/2026-09-12T00:00:00Z',
    'limit': 100, 'query': json.dumps({'eo:cloud_cover': {'lt': 15}}),
    'sortby': '-datetime'})
requests = [('api-data-schema.json', 'https://planetarycomputer.microsoft.com/api/data/v1/openapi.json'),
            ('sentinel-scenes.json', 'https://planetarycomputer.microsoft.com/api/stac/v1/search?' + query),
            ('ana-hydro-service.json', 'https://www.snirh.gov.br/arcgis/rest/services?f=pjson')]
for filename, url in requests:
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            payload = response.read()
        json.loads(payload)
        (OUT / filename).write_bytes(payload)
        print(filename, len(payload), 'bytes', flush=True)
    except Exception as error:
        print(filename, type(error).__name__, str(error), flush=True)

# Download dated, open Sentinel-2 review chips. Request coarse 2 km grid windows,
# not exact site locations. A small bridge may be unresolved at native 10 m GSD.
if (OUT / 'sentinel-scenes.json').exists():
    import math
    from concurrent.futures import ThreadPoolExecutor
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    scenes = json.loads((OUT / 'sentinel-scenes.json').read_text())['features']
    gaps_path = OUT.parent / 'outputs' / 'junction_review.geojson'
    gaps = json.loads(gaps_path.read_text())['features']
    project = Transformer.from_crs(4326, 32723, always_xy=True)
    to_wgs = Transformer.from_crs(32723, 4326, always_xy=True)
    def chip(feature):
        props = feature['properties']
        center = shape(feature['geometry']).centroid
        covering = [s for s in scenes if shape(s['geometry']).contains(center)]
        if not covering:
            return {'gap_id': props['gap_id'], 'status': 'no_scene_in_cached_search'}
        scene = sorted(covering, key=lambda s: s['properties']['datetime'], reverse=True)[0]
        x, y = project.transform(center.x, center.y)
        x = round(x / 1000) * 1000; y = round(y / 1000) * 1000
        bounds = [x-1000, y-1000, x+1000, y+1000]
        params = {'collection': 'sentinel-2-l2a', 'item': scene['id'], 'assets': 'visual',
                  'asset_bidx': 'visual|1,2,3', 'coord_crs': 'EPSG:32723',
                  'dst_crs': 'EPSG:32723', 'resampling': 'nearest'}
        url = 'https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/' + ','.join(map(str,bounds)) + '/600x600.png?' + urllib.parse.urlencode(params)
        filename = props['gap_id'] + '.png'
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                payload = response.read()
            if not payload.startswith(b'\x89PNG'):
                raise ValueError('Expected PNG')
            (OUT / filename).write_bytes(payload)
            print(filename, len(payload), 'bytes', flush=True)
            return {'gap_id': props['gap_id'], 'status': 'downloaded_unreviewed', 'file': filename,
                    'scene_id': scene['id'], 'acquired_at': scene['properties']['datetime'],
                    'scene_cloud_pct': scene['properties']['eo:cloud_cover'],
                    'bounds_utm23s': bounds, 'native_visual_resolution_m': 10, 'url': url,
                    'attribution': 'Contains modified Copernicus Sentinel data, served by Microsoft Planetary Computer.'}
        except Exception as error:
            return {'gap_id': props['gap_id'], 'status': 'download_failed', 'error': str(error)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(chip, gaps))
    (OUT / 'review-imagery.json').write_text(json.dumps(records, indent=2))
    print('Chips:',len([r for r in records if r['status']=='downloaded_unreviewed']),'of',len(records),flush=True)

for folder in ['DADOSABERTOS', 'SNIRH2016']:
    url = 'https://www.snirh.gov.br/arcgis/rest/services/' + folder + '?f=pjson'
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            payload=response.read()
        (OUT / ('ana-' + folder.lower() + '.json')).write_bytes(payload)
        print('ANA folder',folder,len(payload),flush=True)
    except Exception as error:
        print('ANA folder',folder,str(error),flush=True)
