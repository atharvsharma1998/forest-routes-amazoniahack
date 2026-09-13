import unittest
from shapely.geometry import LineString
from forest_routes.core import Road, Network, Router, raw_parts, noded_parts


def road(coords, source='osm', id='test'):
    return Road(LineString(coords), source, id)


class RoutingTests(unittest.TestCase):
    def test_projection_inside_edge_and_reverse_geometry(self):
        n = Network([road([(0, 0), (1000, 0)])])
        r, pieces = Router(n).route((800, 20), (200, 30), 50)
        self.assertTrue(r['candidate_connected'])
        self.assertEqual(r['network_distance_km'], .6)
        self.assertEqual(r['initial_walk_lower_bound_m'], 20)
        self.assertEqual(r['final_walk_lower_bound_m'], 30)
        self.assertEqual(pieces[1][0].coords[0], (800, 0))
        self.assertEqual(pieces[1][0].coords[-1], (200, 0))

    def test_origin_allowance_is_enforced(self):
        n = Network([road([(0, 0), (1000, 0)])])
        r, _ = Router(n).route((0, 200), (1000, 20), 100)
        self.assertFalse(r['candidate_connected'])
        self.assertEqual(r['reason'], 'origin_access_exceeds_allowance')

    def test_gap_threshold_and_no_free_teleport(self):
        n = Network([road([(0, 0), (100, 0)]), road([(251, 0), (400, 0)])])
        n.add_gap_candidates(300)
        rejected, _ = Router(n, 150).route((0, 0), (400, 0), 0)
        self.assertFalse(rejected['candidate_connected'])
        r, pieces = Router(n, 151).route((0, 0), (400, 0), 0)
        self.assertTrue(r['candidate_connected'])
        self.assertEqual(r['proposed_gap_distance_m'], 151)
        self.assertEqual(r['network_distance_km'], .4)
        self.assertAlmostEqual(sum(p[0].length for p in pieces), 400)
        self.assertLess(r['input_geometry_supported_fraction'], 1)
        blocked, _ = Router(n, 151, rejected=set(r['gap_ids'])).route((0, 0), (400, 0), 0)
        self.assertFalse(blocked['candidate_connected'])

    def test_endpoint_to_interior_splits_target(self):
        n = Network([road([(0, 0), (1000, 0)]), road([(500, 100), (500, 500)])])
        n.add_gap_candidates(150)
        r, pieces = Router(n, 150).route((0, 0), (500, 500), 0)
        self.assertEqual(r['network_distance_km'], 1)
        for first, second in zip(pieces, pieces[1:]):
            self.assertLess(LineString([first[0].coords[-1], second[0].coords[0]]).length, 1e-6)

    def test_crossing_is_only_connected_in_planar_scenario(self):
        roads = [road([(0, 0), (1000, 0)]), road([(500, -500), (500, 500)])]
        r, _ = Router(Network(raw_parts(roads))).route((0, 0), (500, 500), 0)
        self.assertFalse(r['candidate_connected'])
        r, _ = Router(Network(noded_parts(roads))).route((0, 0), (500, 500), 0)
        self.assertTrue(r['candidate_connected'])
        self.assertFalse(r['field_verified'])
        self.assertEqual(r['network_distance_km'], 1)

    def test_nearest_disconnected_trace_does_not_hide_reachable_road(self):
        n = Network([road([(0, 0), (1000, 0)]), road([(900, 80), (1100, 80)])])
        r, _ = Router(n).route((0, 0), (1000, 90), 100)
        self.assertTrue(r['candidate_connected'])
        self.assertEqual(r['nearest_destination_network_m'], 10)
        self.assertEqual(r['final_walk_lower_bound_m'], 90)

    def test_parallel_edges_are_not_summed(self):
        n = Network([road([(0, 0), (100, 0)]), road([(0, 0), (50, 20), (100, 0)]), road([(100, 0), (200, 0)])])
        r, _ = Router(n).route((0, 0), (200, 0), 0)
        self.assertEqual(r['network_distance_km'], .2)


if __name__ == '__main__':
    unittest.main()
