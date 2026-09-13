"""Metric, provenance-preserving geometry benchmark. No network services at runtime."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import time

import numpy as np
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
import shapely
from shapely.geometry import LineString, Point, shape
from shapely.ops import substring, transform
from shapely.strtree import STRtree

PROJECT = Transformer.from_crs(4326, 32723, always_xy=True)
UNPROJECT = Transformer.from_crs(32723, 4326, always_xy=True)
NON_VEHICLE = {'footway', 'path', 'steps', 'pedestrian', 'cycleway', 'bridleway',
               'construction', 'proposed', 'bus_stop', 'platform'}


def key(xy):
    # 0.1 micrometre numerical precision, not a physical snapping allowance.
    return tuple(round(float(v), 7) for v in xy[:2])


@dataclass
class Road:
    geometry: LineString
    source: str
    source_id: str
    highway: str | None = None


@dataclass
class Edge:
    u: int
    v: int
    geometry: LineString
    source: str
    source_id: str
    gap_id: str | None = None

    @property
    def length(self):
        return self.geometry.length


def load_roads(directory, vehicle_only=False):
    roads, inventory = [], {}
    for source, filename in [('osm', 'roads-osm-paragominas.geojson'),
                             ('previsia', 'roads-previsia-2025-paragominas.geojson')]:
        path = directory / filename
        data = json.loads(path.read_text())
        features = data['features']
        lengths = []
        excluded = 0
        for i, feature in enumerate(features):
            geom = transform(PROJECT.transform, shape(feature['geometry']))
            if not geom.is_valid or geom.is_empty or geom.length <= 0:
                raise ValueError(f'Invalid or zero-length road {source}:{i}')
            lengths.append(geom.length)
            props = feature['properties']
            highway = props.get('highway')
            if vehicle_only and source == 'osm' and highway in NON_VEHICLE:
                excluded += 1
                continue
            roads.append(Road(geom, source, f'{source}:{i}', highway))
        inventory[source] = {'features': len(features), 'length_km': sum(lengths) / 1000,
                             'excluded_features': excluded,
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'property_keys': sorted({k for f in features for k in f['properties']})}
    return roads, inventory


def raw_parts(roads):
    """Connect exactly shared vertices; preserve intermediate bends as geometry."""
    counts = Counter(key(c) for r in roads for c in r.geometry.coords)
    result = []
    for road in roads:
        coords = list(road.geometry.coords)
        start = 0
        for i in range(1, len(coords)):
            if i == len(coords) - 1 or counts[key(coords[i])] > 1:
                part = LineString(coords[start:i + 1])
                if part.length > 1e-7:
                    result.append(Road(part, road.source, road.source_id, road.highway))
                start = i
    return result


def noded_parts(roads):
    """Planar intersections are geometric hypotheses, not proven junctions."""
    geoms = [r.geometry for r in roads]
    parts = list(shapely.union_all(geoms).geoms)
    tree = STRtree(geoms)
    mids = shapely.line_interpolate_point(parts, 0.5, normalized=True)
    # A noded part lies within an input feature. Match its interior; prefer OSM
    # for coincident geometry. Input order is deterministic (OSM, then PrevisIA).
    matches, distances = tree.query_nearest(mids, all_matches=True, return_distance=True)
    owners = np.full(len(parts), len(roads), dtype=np.int64)
    np.minimum.at(owners, matches[0], matches[1])
    if np.max(distances, initial=0) > 0.001:
        raise ValueError('Noded part could not be attributed to an input road')
    return [Road(g, roads[int(i)].source, roads[int(i)].source_id,
                 roads[int(i)].highway) for g, i in zip(parts, owners) if g.length > 1e-7]


class Network:
    def __init__(self, parts):
        self.coords = []
        self.node_ids = {}
        self.edges = []
        for p in parts:
            self.add(p.geometry, p.source, p.source_id)
        self.candidates = []

    def node(self, coordinate):
        k = key(coordinate)
        if k not in self.node_ids:
            self.node_ids[k] = len(self.coords)
            self.coords.append(k)
        return self.node_ids[k]

    def add(self, geometry, source, source_id, gap_id=None):
        if geometry.length <= 1e-7:
            return
        self.edges.append(Edge(self.node(geometry.coords[0]), self.node(geometry.coords[-1]),
                               geometry, source, source_id, gap_id))

    def view(self, tolerance=0, rejected=None):
        rejected = rejected or set()
        chosen = {}
        for i, edge in enumerate(self.edges):
            if edge.gap_id and (edge.length > tolerance + 1e-7 or edge.gap_id in rejected):
                continue
            if edge.u == edge.v:
                continue
            # Parallel edges: choose the shortest weighted edge, never sum them.
            cost = edge.length * (5 if edge.gap_id else 1)
            pair = tuple(sorted((edge.u, edge.v)))
            if pair not in chosen or cost < chosen[pair][0]:
                chosen[pair] = (cost, i)
        a, b, w = [], [], []
        lookup = {}
        for (u, v), (cost, i) in chosen.items():
            a.extend([u, v]); b.extend([v, u]); w.extend([cost, cost])
            lookup[(u, v)] = lookup[(v, u)] = i
        matrix = coo_matrix((w, (a, b)), shape=(len(self.coords), len(self.coords))).tocsr()
        n, labels = connected_components(matrix, directed=False)
        lengths = np.zeros(n)
        for edge in self.edges:
            if not edge.gap_id:
                lengths[labels[edge.u]] += edge.length
        node_counts = np.bincount(labels, minlength=n)
        stats = {'components': int(n), 'nodes': len(self.coords),
                 'graph_edges': len(chosen), 'largest_component_node_share': float(node_counts.max() / len(labels)),
                 'largest_component_length_share': float(lengths.max() / lengths.sum()) if lengths.sum() else 0,
                 'active_gap_edges': sum(self.edges[i].gap_id is not None for _, i in chosen.values())}
        return matrix, labels, lookup, stats

    def add_gap_candidates(self, max_gap=300, max_neighbors=3):
        """Connect dangling endpoints to up to three other base components.

        Keep connectors explicit, split the target line at its projection, and
        retain their full physical distance. Never displace the source geometry.
        """
        _, labels, _, _ = self.view()
        degree = np.zeros(len(self.coords), dtype=int)
        for e in self.edges:
            degree[e.u] += 1; degree[e.v] += 1
        tree = STRtree([e.geometry for e in self.edges])
        candidates = []
        seen = set()
        for u in np.flatnonzero(degree == 1):
            point = Point(self.coords[u])
            nearest_by_component = {}
            for target in tree.query(point, predicate='dwithin', distance=max_gap):
                edge = self.edges[target]
                comp = labels[edge.u]
                if comp == labels[u]:
                    continue
                s = edge.geometry.project(point)
                q = edge.geometry.interpolate(s)
                distance = point.distance(q)
                if distance <= 1e-7:
                    continue
                entry = (distance, int(target), s, q)
                if comp not in nearest_by_component or entry[:3] < nearest_by_component[comp][:3]:
                    nearest_by_component[comp] = entry
            for distance, target, s, q in sorted(nearest_by_component.values(), key=lambda e: e[:3])[:max_neighbors]:
                endpoints = tuple(sorted((key(point.coords[0]), key(q.coords[0]))))
                if endpoints in seen:
                    continue
                seen.add(endpoints)
                gap_id = 'gap-' + hashlib.sha256(repr(endpoints).encode()).hexdigest()[:12]
                candidates.append({'id': gap_id, 'u': int(u), 'target': target, 's': s,
                                   'geometry': LineString([point, q]), 'distance_m': distance})
        cuts = defaultdict(list)
        for c in candidates:
            cuts[c['target']].append(c['s'])
        old = self.edges
        self.edges = []
        for i, e in enumerate(old):
            positions = sorted(set([0., e.length] + cuts.get(i, [])))
            for a, b in zip(positions, positions[1:]):
                if b - a > 1e-7:
                    self.add(substring(e.geometry, a, b), e.source, e.source_id)
        for c in candidates:
            self.add(c['geometry'], 'proposed_gap', c['id'], c['id'])
        self.candidates = candidates
        return len(candidates)


class Router:
    def __init__(self, network, tolerance=0, max_walk=3000, rejected=None):
        self.network = network
        self.matrix, self.labels, self.lookup, self.stats = network.view(tolerance, rejected)
        self.road_ids = [i for i, e in enumerate(network.edges) if not e.gap_id]
        self.tree = STRtree([network.edges[i].geometry for i in self.road_ids])
        self.max_walk = max_walk
        self.access_cache = {}
        self.distance_cache = {}

    def access(self, xy):
        k = key(xy)
        if k in self.access_cache:
            return self.access_cache[k]
        p = Point(xy)
        best = {}
        for j in self.tree.query(p, predicate='dwithin', distance=self.max_walk):
            i = self.road_ids[j]; e = self.network.edges[i]
            s = e.geometry.project(p); q = e.geometry.interpolate(s)
            distance = p.distance(q); comp = int(self.labels[e.u])
            option = (distance, i, s, q)
            if comp not in best or option[:3] < best[comp][:3]:
                best[comp] = option
        j = int(self.tree.nearest(p))
        nearest = p.distance(self.network.edges[self.road_ids[j]].geometry)
        self.access_cache[k] = (best, nearest)
        return best, nearest

    def paths_from(self, node):
        if node not in self.distance_cache:
            # Bound memory: up to 10 cached single-source arrays per scenario.
            if len(self.distance_cache) >= 10:
                self.distance_cache.pop(next(iter(self.distance_cache)))
            self.distance_cache[node] = dijkstra(self.matrix, directed=False, indices=node,
                                                  return_predecessors=True)
        return self.distance_cache[node]

    def between(self, start, end):
        _, ai, sa, _ = start; _, bi, sb, _ = end
        a = self.network.edges[ai]; b = self.network.edges[bi]
        choices = []
        if ai == bi:
            choices.append((abs(sb - sa), None, None))
        for u, da in [(a.u, sa), (a.v, a.length - sa)]:
            distances, _ = self.paths_from(u)
            for v, db in [(b.u, sb), (b.v, b.length - sb)]:
                if np.isfinite(distances[v]):
                    choices.append((da + distances[v] + db, u, v))
        if not choices:
            return None
        cost, u, v = min(choices, key=lambda x: x[0])
        pieces = []
        def add(geometry, edge):
            if geometry.geom_type == 'LineString' and geometry.length > 1e-7:
                pieces.append((geometry, edge))
        if u is None:
            add(substring(a.geometry, sa, sb), a)
        else:
            add(substring(a.geometry, sa, 0 if u == a.u else a.length), a)
            _, pred = self.paths_from(u)
            nodes = [v]
            while nodes[-1] != u:
                prev = int(pred[nodes[-1]])
                if prev < 0:
                    raise ValueError('Broken predecessor chain')
                nodes.append(prev)
            nodes.reverse()
            for n1, n2 in zip(nodes, nodes[1:]):
                e = self.network.edges[self.lookup[(n1, n2)]]
                geom = e.geometry if n1 == e.u else LineString(list(e.geometry.coords)[::-1])
                add(geom, e)
            add(substring(b.geometry, 0 if v == b.u else b.length, sb), b)
        return cost, pieces

    def route(self, origin, destination, allowance):
        started = time.perf_counter()
        origins, nearest_origin = self.access(origin)
        destinations, nearest_dest = self.access(destination)
        common = origins.keys() & destinations.keys()
        eligible = [c for c in common if origins[c][0] <= allowance + 1e-7 and destinations[c][0] <= allowance + 1e-7]
        result = {'status': 'no_candidate', 'walking_allowance_per_end_m': allowance,
                  'nearest_origin_network_m': round(nearest_origin, 2),
                  'nearest_destination_network_m': round(nearest_dest, 2),
                  'initial_walk_lower_bound_m': None, 'final_walk_lower_bound_m': None,
                  'network_distance_km': None, 'proposed_gap_distance_m': None,
                  'max_gap_m': None, 'gap_count': None, 'input_geometry_supported_fraction': None,
                  'candidate_connected': False, 'field_verified': False,
                  'walking_model': 'straight-line lower bound; terrain and access unverified'}
        if not eligible:
            if nearest_origin > allowance:
                result['reason'] = 'origin_access_exceeds_allowance'
            elif nearest_dest > allowance:
                result['reason'] = 'destination_access_exceeds_allowance'
            else:
                result['reason'] = 'no_shared_component_within_both_access_allowances'
            if common:
                # A diagnostic, not a claimed route under the chosen policy.
                c = min(common, key=lambda c: max(origins[c][0], destinations[c][0]))
                result['best_common_component_initial_m'] = round(origins[c][0], 2)
                result['best_common_component_final_m'] = round(destinations[c][0], 2)
            result['query_ms'] = round((time.perf_counter() - started) * 1000, 2)
            return result, []
        options = []
        for c in sorted(eligible):
            route = self.between(origins[c], destinations[c])
            if route is not None:
                cost, pieces = route
                options.append((cost + 10 * (origins[c][0] + destinations[c][0]), c, pieces))
        if not options:
            result['reason'] = 'disconnected_after_attachment'
            result['query_ms'] = round((time.perf_counter() - started) * 1000, 2)
            return result, []
        _, c, pieces = min(options, key=lambda x: x[0])
        network_m = sum(g.length for g, _ in pieces)
        gaps = [(g, e) for g, e in pieces if e.gap_id]
        gap_m = sum(g.length for g, _ in gaps)
        result.update(status='candidate_requires_validation', reason='geometry_only', candidate_connected=True,
                      initial_walk_lower_bound_m=round(origins[c][0], 2),
                      final_walk_lower_bound_m=round(destinations[c][0], 2),
                      network_distance_km=round(network_m / 1000, 4),
                      proposed_gap_distance_m=round(gap_m, 2),
                      max_gap_m=round(max((g.length for g, _ in gaps), default=0), 2),
                      gap_count=len(gaps), gap_ids=[e.gap_id for _, e in gaps],
                      input_geometry_supported_fraction=round((network_m - gap_m) / network_m, 6) if network_m else None,
                      query_ms=round((time.perf_counter() - started) * 1000, 2))
        output = []
        if origins[c][0] > 1e-7:
            output.append((LineString([origin, origins[c][3].coords[0]]), 'initial_walk_lower_bound', None))
        output.extend((g, e.source, e.gap_id) for g, e in pieces)
        if destinations[c][0] > 1e-7:
            output.append((LineString([destinations[c][3].coords[0], destination]), 'final_walk_lower_bound', None))
        return result, output
