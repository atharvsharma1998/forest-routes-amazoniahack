"""Build offline Sentinel-2 overview layers for the field-officer map (local TIFs only)."""
from __future__ import annotations
import base64, csv, io, json
from pathlib import Path
from PIL import Image
from pyproj import Transformer
from forest_routes.core import PROJECT

Image.MAX_IMAGE_PIXELS = 150_000_000
P = Path(__file__).resolve().parents[1] / 'private'
TILES = P / 'satellite_tiles'
OUT = P / 'imagery'
OUT.mkdir(parents=True, exist_ok=True)


def road_bounds(map_roads_path: Path, pad=5000):
    roads = json.loads(map_roads_path.read_text())
    xs, ys = [], []
    for road in roads:
        for x, y in road['coordinates']:
            xs.append(x); ys.append(y)
    return [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]


def load_tiles(meta):
    opened = []
    for t in meta:
        if t.get('status') != 'downloaded':
            continue
        path = TILES / t['file']
        if not path.exists():
            continue
        opened.append({
            'meta': t,
            'im': Image.open(path).convert('RGB'),
            'to_tile': Transformer.from_crs(32723, t['epsg'], always_xy=True),
        })
        print('loaded', t['file'], flush=True)
    return opened


def tile_window(tile, bounds23):
    """Return pixel box in tile image for EPSG:32723 bounds, or None if no overlap."""
    t = tile['meta']
    a, _, x0, _, e, y0 = t['transform']
    corners = [
        tile['to_tile'].transform(bounds23[0], bounds23[1]),
        tile['to_tile'].transform(bounds23[0], bounds23[3]),
        tile['to_tile'].transform(bounds23[2], bounds23[1]),
        tile['to_tile'].transform(bounds23[2], bounds23[3]),
    ]
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
    cols = [(x - x0) / a for x in xs]
    rows = [(y - y0) / e for y in ys]
    im = tile['im']
    left, right = max(0, int(min(cols))), min(im.width, int(max(cols)) + 1)
    top, bottom = max(0, int(min(rows))), min(im.height, int(max(rows)) + 1)
    if right - left < 8 or bottom - top < 8:
        return None
    # geographic extent of the retained pixel window, back in 32723
    from_tile = Transformer.from_crs(t['epsg'], 32723, always_xy=True)
    x_a, y_a = from_tile.transform(x0 + left * a, y0 + top * e)
    x_b, y_b = from_tile.transform(x0 + (right - 1) * a, y0 + (bottom - 1) * e)
    return {
        'box': (left, top, right, bottom),
        'bounds': [min(x_a, x_b), min(y_a, y_b), max(x_a, x_b), max(y_a, y_b)],
        'prefer': 0 if t['epsg'] == 32723 else 1,
    }


def render_window(tiles, bounds, max_side=900, jpeg_quality=76):
    minx, miny, maxx, maxy = bounds
    width_m, height_m = maxx - minx, maxy - miny
    scale = max(width_m, height_m) / max_side
    w = max(48, int(round(width_m / scale)))
    h = max(48, int(round(height_m / scale)))
    canvas = Image.new('RGB', (w, h), (42, 50, 44))

    parts = []
    for tile in tiles:
        win = tile_window(tile, bounds)
        if not win:
            continue
        crop = tile['im'].crop(win['box'])
        parts.append((win['prefer'], win['bounds'], crop))
    parts.sort(key=lambda p: p[0])  # 32723 first, then others underneath conceptually — paint 32722 first then 32723 on top
    parts.sort(key=lambda p: -p[0])  # paint preferred last

    for _, pb, crop in parts:
        # Map crop bounds onto canvas pixels
        x0 = int((pb[0] - minx) / scale)
        x1 = int((pb[2] - minx) / scale)
        y0 = int((maxy - pb[3]) / scale)
        y1 = int((maxy - pb[1]) / scale)
        if x1 <= x0 or y1 <= y0:
            continue
        resized = crop.resize((max(1, x1 - x0), max(1, y1 - y0)), Image.BILINEAR)
        canvas.paste(resized, (x0, y0))

    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
    return {
        'bounds_utm23s': [round(v, 1) for v in bounds],
        'width_px': w, 'height_px': h,
        'approx_resolution_m': round(scale, 1),
        'data_uri': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
        'bytes': len(buf.getvalue()),
        'acquired_at': '2026-09-03T13:42:21.024000Z',
        'source': 'Copernicus Sentinel-2 L2A visual (local municipal tiles)',
        'native_resolution_m': 10,
        'note': 'Downsampled overview for offline review; not bridge-scale evidence.'
    }


def main():
    meta = json.loads((TILES / 'manifest.json').read_text())['tiles']
    print('Loading tiles…', flush=True)
    tiles = load_tiles(meta)
    roads_path = P / 'reviewed' / 'map_roads.json'
    if not roads_path.exists():
        roads_path = P / 'outputs' / 'map_roads.json'
    municipal = road_bounds(roads_path, pad=5000)
    print('Municipal bounds', [round(v) for v in municipal], flush=True)
    overview = render_window(tiles, municipal, max_side=1100, jpeg_quality=70)
    overview.update(id='municipal-overview', kind='municipal')
    print('overview', overview['width_px'], 'x', overview['height_px'], overview['bytes'], 'B', flush=True)

    pair_path = Path(__file__).resolve().parents[2] / 'Incubation material' / 'Challenge 3' / 'test-pairs.csv'
    pairs = list(csv.DictReader(pair_path.open()))
    routes_geo = P / 'reviewed' / 'routes.geojson'
    if not routes_geo.exists():
        routes_geo = P / 'outputs' / 'routes.geojson'
    feats = json.loads(routes_geo.read_text())['features'] if routes_geo.exists() else []

    journey_layers = []
    for pair in pairs:
        pid = pair['id']
        ox, oy = PROJECT.transform(float(pair['origin_lon']), float(pair['origin_lat']))
        dx, dy = PROJECT.transform(float(pair['dest_lon']), float(pair['dest_lat']))
        xs, ys = [ox, dx], [oy, dy]
        for f in feats:
            if f['properties'].get('pair_id') != pid:
                continue
            for lon, lat in f['geometry']['coordinates']:
                x, y = PROJECT.transform(lon, lat)
                xs.append(x); ys.append(y)
        bounds = [min(xs) - 4500, min(ys) - 4500, max(xs) + 4500, max(ys) + 4500]
        layer = render_window(tiles, bounds, max_side=760, jpeg_quality=74)
        layer.update(id=pid, kind='journey')
        journey_layers.append(layer)
        print(pid, layer['bytes'], 'B @', layer['approx_resolution_m'], 'm/px', flush=True)

    payload = {
        'crs': 'EPSG:32723',
        'field_verified': False,
        'municipal': overview,
        'journeys': journey_layers,
        'limitations': [
            'Downsampled from native 10 m Sentinel-2 visual tiles for offline inspection.',
            'Not suitable as sole evidence for bridges or sub-pixel junctions.',
            'Source tiles may span UTM 22S/23S; displayed in EPSG:32723 for this municipality.'
        ]
    }
    path = OUT / 'satellite-layer.json'
    path.write_text(json.dumps(payload))
    print('Wrote', path, 'total', path.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    main()
