"""Generate a single-file offline inspector; no CDN, fonts, tiles, or telemetry."""
import json
import base64
from pathlib import Path
from .core import PROJECT


def make_report(output, pairs):
    summary = json.loads((output / 'summary.json').read_text())
    routes_path = output / 'routes.json'
    if not routes_path.exists():
        return
    routes = json.loads(routes_path.read_text())
    roads = json.loads((output / 'map_roads.json').read_text())
    features = json.loads((output / 'routes.geojson').read_text())['features']
    line_data = []
    for feature in features:
        line_data.append({**feature['properties'], 'coordinates': [list(PROJECT.transform(*c)) for c in feature['geometry']['coordinates']]})
    sites = [{'id': p['id'], 'origin': list(PROJECT.transform(float(p['origin_lon']), float(p['origin_lat']))),
              'destination': list(PROJECT.transform(float(p['dest_lon']), float(p['dest_lat'])))} for p in pairs]
    review_dir = output.parent / 'imagery'
    reviews = json.loads((review_dir / 'visual-review.json').read_text()) if (review_dir / 'visual-review.json').exists() else []
    imagery = []
    if (review_dir / 'review-imagery.json').exists():
        for record in json.loads((review_dir / 'review-imagery.json').read_text()):
            if record.get('file') and (review_dir / record['file']).exists():
                imagery.append({k: record[k] for k in ['gap_id', 'bounds_utm23s', 'acquired_at', 'scene_id']})
                imagery[-1]['data_uri'] = 'data:image/png;base64,' + base64.b64encode((review_dir / record['file']).read_bytes()).decode()
    satellite = None
    sat_path = review_dir / 'satellite-layer.json'
    if sat_path.exists():
        satellite = json.loads(sat_path.read_text())
    payload = {'summary': summary, 'routes': routes, 'roads': roads, 'lines': line_data,
               'sites': sites, 'reviews': reviews, 'imagery': imagery, 'satellite': satellite}
    template = Path(__file__).with_name('report_template.html').read_text()
    (output / 'report.html').write_text(template.replace('__PAYLOAD__', json.dumps(payload, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')))
