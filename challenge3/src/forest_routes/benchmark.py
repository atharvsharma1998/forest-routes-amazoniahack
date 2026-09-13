"""Run: PYTHONPATH=challenge3/src python3 -m forest_routes.benchmark"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform
import resource
import time

import numpy as np
import scipy
import shapely
from shapely.geometry import mapping
from shapely.ops import transform

from .core import Network, Router, PROJECT, UNPROJECT, load_roads, noded_parts, raw_parts


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False))


def evaluate(network, name, tolerance, pairs, allowances, output, all_rows, summaries, rejected):
    print(f'Evaluating {name} ...', flush=True)
    router = Router(network, tolerance, max(allowances), rejected)
    for allowance in allowances:
        rows = []
        features = []
        for pair in pairs:
            origin = PROJECT.transform(float(pair['origin_lon']), float(pair['origin_lat']))
            dest = PROJECT.transform(float(pair['dest_lon']), float(pair['dest_lat']))
            row, pieces = router.route(origin, dest, allowance)
            row.update(pair_id=pair['id'], pair_type=pair['type'], scenario=name,
                       snap_tolerance_m=tolerance, straight_line_km=float(pair['straight_line_km']))
            if row['network_distance_km'] is not None:
                total = row['network_distance_km'] + (row['initial_walk_lower_bound_m'] + row['final_walk_lower_bound_m']) / 1000
                row['total_distance_lower_bound_km'] = round(total, 4)
                row['detour_ratio'] = round(total / row['straight_line_km'], 4)
            rows.append(row)
            if allowance == 1000 and name == 'fused_noded_snap150':
                for g, kind, gap in pieces:
                    features.append({'type': 'Feature', 'geometry': mapping(transform(UNPROJECT.transform, g)),
                                     'properties': {'pair_id': pair['id'], 'kind': kind, 'gap_id': gap,
                                                    'length_m': round(g.length, 2), 'validation': 'unverified'}})
        if allowance == 1000 and name == 'fused_noded_snap150':
            write_json(output / 'routes.geojson', {'type': 'FeatureCollection', 'features': features})
            write_json(output / 'routes.json', rows)
        all_rows.extend(rows)
        item = {'scenario': name, 'snap_tolerance_m': tolerance, 'walking_allowance_per_end_m': allowance,
                'candidate_pairs': sum(r['candidate_connected'] for r in rows), 'tested_pairs': len(pairs),
                'field_verified_pairs': 0, **router.stats,
                'query_p50_ms': round(float(np.median([r['query_ms'] for r in rows])), 2),
                'query_max_ms': max(r['query_ms'] for r in rows)}
        summaries.append(item)
        print(f"  {allowance:4g} m walk/end: {item['candidate_pairs']}/{len(pairs)} geometric candidates", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[3]
    parser.add_argument('--data-dir', type=Path, default=root / 'Incubation material' / 'Challenge 3')
    parser.add_argument('--output', type=Path, default=root / 'challenge3' / 'private' / 'outputs')
    parser.add_argument('--vehicle-only', action='store_true', help='Exclude explicitly nonvehicle OSM classes; default preserves supplied OSM for comparison.')
    parser.add_argument('--allowances', nargs='+', type=float, default=[400, 500, 1000, 2000, 3000])
    parser.add_argument('--reject-gaps', type=Path, help='JSON list of stable gap IDs to remove (e.g. reviewer rejected bridge).')
    parser.add_argument('--screened-gaps', type=Path, help='Allow only these screened candidate gap IDs; none is a field approval.')
    parser.add_argument('--export-graph', action='store_true', help='Export the compact offline graph after policy filtering.')
    parser.add_argument('--field-roads', type=Path, help='Accepted local GPX-derived GeoJSON from the feedback module.')
    args = parser.parse_args()
    if any(not np.isfinite(a) or a < 0 for a in args.allowances):
        parser.error('Walking allowances must be finite and nonnegative')
    if 1000 not in args.allowances:
        parser.error('Include 1000 in --allowances for the default-policy map report')
    args.allowances = sorted(set(args.allowances))
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    roads, inventory = load_roads(args.data_dir, args.vehicle_only)
    if args.field_roads:
        from .core import Road
        from shapely.geometry import shape
        field = json.loads(args.field_roads.read_text())
        for i, f in enumerate(field['features']):
            if f['properties'].get('decision') != 'accepted':
                raise ValueError('Only explicitly reviewed field-road proposals can enter this comparison')
            if f['properties'].get('synthetic'):
                raise ValueError('Synthetic GPS must not be mixed into the real challenge benchmark')
            roads.append(Road(transform(PROJECT.transform, shape(f['geometry'])), 'field_gps', 'field:' + f['properties']['record_id'] + ':' + str(i)))
    pair_path = args.data_dir / 'test-pairs.csv'
    with pair_path.open() as f:
        pairs = list(csv.DictReader(f))
    rejected = set(json.loads(args.reject_gaps.read_text())) if args.reject_gaps else set()
    rows, summaries, build_times = [], [], {}
    for source in ['osm', 'previsia']:
        t = time.perf_counter()
        net = Network(raw_parts([r for r in roads if r.source == source]))
        build_times[source + '_raw_seconds'] = round(time.perf_counter() - t, 3)
        evaluate(net, source + '_raw', 0, pairs, args.allowances, args.output, rows, summaries, rejected)
        del net
    t = time.perf_counter()
    net = Network(raw_parts(roads))
    build_times['fused_shared_vertices_seconds'] = round(time.perf_counter() - t, 3)
    evaluate(net, 'fused_shared_vertices', 0, pairs, args.allowances, args.output, rows, summaries, rejected)
    del net
    t = time.perf_counter()
    net = Network(noded_parts(roads))
    build_times['fused_planar_noding_seconds'] = round(time.perf_counter() - t, 3)
    evaluate(net, 'fused_noded', 0, pairs, args.allowances, args.output, rows, summaries, rejected)
    t = time.perf_counter()
    gap_count = net.add_gap_candidates(300)
    build_times['gap_preparation_seconds'] = round(time.perf_counter() - t, 3)
    explicitly_rejected = set(rejected)
    if args.screened_gaps:
        allowed = set(json.loads(args.screened_gaps.read_text()))
        rejected |= {c['id'] for c in net.candidates} - allowed
    if args.export_graph:
        from .portable import export_graph
        export_graph(net, args.output, pairs, rejected, 150)
    for tolerance in [50, 150, 300]:
        evaluate(net, f'fused_noded_snap{tolerance}', tolerance, pairs, args.allowances,
                 args.output, rows, summaries, rejected)
    write_json(args.output / 'all_results.json', rows)
    keys = sorted({k for r in rows for k in r})
    with (args.output / 'per_pair.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader()
        writer.writerows({**r, 'gap_ids': '|'.join(r.get('gap_ids', []))} for r in rows)
    gap_use = Counter(gap for r in rows if r['scenario'] == 'fused_noded_snap150'
                      and r['walking_allowance_per_end_m'] == 1000 for gap in r.get('gap_ids', []))
    gap_features = []
    for c in sorted(net.candidates, key=lambda c: (-gap_use[c['id']], c['distance_m'])):
        if gap_use[c['id']] == 0:
            continue
        gap_features.append({'type': 'Feature', 'geometry': mapping(transform(UNPROJECT.transform, c['geometry'])),
                             'properties': {'gap_id': c['id'], 'length_m': round(c['distance_m'], 2),
                                            'used_by_pair_count': gap_use[c['id']],
                                            'review_status': 'unreviewed', 'evidence': None}})
    package_root = Path(__file__).resolve().parents[2]
    ledger_path = package_root / 'private/evidence/gap-review-ledger.json'
    if not ledger_path.exists():
        ledger_path = package_root / 'evidence/gap-review-ledger.json'
    if ledger_path.exists():
        ledger = {r['gap_id']: r for r in json.loads(ledger_path.read_text())}
        for f in gap_features:
            review = ledger.get(f['properties']['gap_id'])
            if review:
                f['properties'].update(review_status=review['decision'], evidence=review)
    write_json(args.output / 'junction_review.geojson', {'type': 'FeatureCollection', 'features': gap_features})
    # Compact local geometry for a completely offline canvas inspector. All supplied
    # coordinates remain private; simplification is ONLY for overview drawing.
    map_lines = [{'source': r.source, 'coordinates': [[round(x, 1), round(y, 1)] for x, y in r.geometry.simplify(15).coords]} for r in roads]
    write_json(args.output / 'map_roads.json', map_lines)
    manifest = {'crs': 'EPSG:32723', 'input_inventory': inventory,
                'pairs_sha256': hashlib.sha256(pair_path.read_bytes()).hexdigest(),
                'vehicle_only': args.vehicle_only,
                'excluded_osm_classes': sorted(__import__('forest_routes.core', fromlist=['NON_VEHICLE']).NON_VEHICLE) if args.vehicle_only else [],
                'run_seconds': round(time.perf_counter() - started, 3), 'build_seconds': build_times,
                'peak_rss_mb_linux': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                'platform': platform.platform(), 'python': platform.python_version(),
                'versions': {'numpy': np.__version__, 'scipy': scipy.__version__, 'shapely': shapely.__version__},
                'gap_candidates_up_to_300m': gap_count,
                'rejected_gap_ids': sorted(explicitly_rejected),
                'withheld_unscreened_gap_count': len(rejected - explicitly_rejected),
                'gap_review_ledger': str(args.screened_gaps) if args.screened_gaps else None,
                'cost': {'external_api_calls_per_route': 0, 'external_api_charge_per_route': 0,
                         'currency': 'USD', 'hardware_energy_preparation_review_cost': 'not priced'},
                'limitations': ['Geometric candidates only; zero field-verified routes.',
                                'All crossings noded in planar scenarios; grade separation unverified.',
                                'Trace acquisition date, passability, access, direction and bridges unknown.',
                                'Walking segments are Euclidean lower bounds, not known walkable paths.',
                                '1km access at BOTH ends assumes walking to/from road transport; field logistics unverified.',
                                'Gap candidates use degree-one endpoints, nearest edge per other base component, at most three targets.',
                                'Route chooses nearest attachment per current component; no continuous optimisation of access along entire road.',
                                'Road cost = metres; proposed gap cost = 5 x metres; walking access cost = 10 x metres. These are planning weights, not travel times.',
                                'Runtime and RAM measured on desktop; Android routing not validated.',
                                'Input geometry support is not independent imagery validation.',
                                'Shared-vertex and noded graphs use a 0.1 micrometre coordinate key for floating-point stability.'],
                'summaries': summaries}
    write_json(args.output / 'summary.json', manifest)
    from .report import make_report
    make_report(args.output, pairs)
    print(f'Finished in {manifest["run_seconds"]} s; local report: {args.output / "report.html"}', flush=True)


if __name__ == '__main__':
    main()
