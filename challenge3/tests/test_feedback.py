import tempfile,unittest
from pathlib import Path
from shapely.geometry import LineString
from forest_routes.feedback import import_gpx,review,accepted_roads
from forest_routes.core import Road,Network,Router
class FeedbackTests(unittest.TestCase):
 def test_proposal_cannot_enter_graph_until_reviewed_and_can_be_revoked(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'track.gpx';p.write_text('<gpx><trk><trkseg><trkpt lat="0" lon="0.001"/><trkpt lat="0" lon="0.002"/></trkseg></trk></gpx>')
   proposal=import_gpx(p,synthetic=True)
  self.assertEqual(len(accepted_roads([proposal])['features']),0)
  accepted=review(proposal,'accepted','Synthetic fixture reviewer','Known generated connector; no real field claim')
  self.assertEqual(len(accepted_roads([accepted])['features']),1)
  revoked=review(accepted,'rejected','Synthetic fixture reviewer','Simulated closure')
  self.assertEqual(len(accepted_roads([revoked])['features']),0)
  self.assertEqual(len(revoked['history']),3)
 def test_real_connectivity_change_on_held_out_synthetic_pair(self):
  roads=[Road(LineString([(0,0),(100,0)]),'osm','a'),Road(LineString([(200,0),(300,0)]),'osm','b')]
  r,_=Router(Network(roads)).route((0,0),(300,0),0);self.assertFalse(r['candidate_connected'])
  roads.append(Road(LineString([(100,0),(200,0)]),'field_gps','reviewed-fixture'))
  r,_=Router(Network(roads)).route((0,0),(300,0),0);self.assertTrue(r['candidate_connected']);self.assertEqual(r['network_distance_km'],.3)
 def test_invalid_coordinates_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.gpx';p.write_text('<gpx><trk><trkseg><trkpt lat="nan" lon="0"/><trkpt lat="0" lon="1"/></trkseg></trk></gpx>')
   with self.assertRaises(ValueError):import_gpx(p)
if __name__=='__main__':unittest.main()
