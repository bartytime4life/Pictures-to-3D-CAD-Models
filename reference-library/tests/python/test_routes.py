"""Route finder rules (cadkit.routes); the Node suite checks the JavaScript twin."""
import json
import subprocess
import sys
import unittest

import _helpers  # noqa: F401
from _helpers import ROOT
from cadkit import routes

DATA = routes.load_routes()


class RouteFinder(unittest.TestCase):
    def test_every_combination_resolves(self):
        recs = routes.all_recommendations(DATA)
        self.assertEqual(len(recs), len(DATA["inputs"]) * len(DATA["goals"]))
        for r in recs:
            self.assertGreaterEqual(len(r["workflows"]), 1)
            self.assertEqual(len(r["workflows"]), len(set(r["workflows"])))
            self.assertEqual(len(r["sections"]), len(r["workflows"]))
            self.assertTrue(r["sources"])

    def test_goal_leads_and_pair_overrides(self):
        self.assertEqual(routes.recommend(DATA, "photo-set", "mount")["workflows"], ["E", "C"])
        self.assertEqual(routes.recommend(DATA, "flat-image", "holder")["workflows"], ["H", "A"])
        self.assertEqual(routes.recommend(DATA, "mesh", "decorative")["workflows"], ["C"])
        self.assertEqual(routes.recommend(DATA, "photo-set", "editable")["workflows"], ["C", "D"])
        self.assertTrue(routes.recommend(DATA, "artwork", "replacement")["warnings"])
        self.assertEqual(routes.recommend(DATA, "multi-view", "editable")["warnings"], [])

    def test_unknown_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            routes.recommend(DATA, "telepathy", "holder")
        with self.assertRaises(ValueError):
            routes.recommend(DATA, "mesh", "world-peace")

    def test_cli(self):
        out = subprocess.run([sys.executable, "-m", "cadkit", "route", "--input", "volume", "--goal", "replacement", "--json"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        r = json.loads(out)
        self.assertEqual(r["workflows"], ["V"])
        self.assertIn("clinical", r["warnings"][0])
        text = subprocess.run([sys.executable, "-m", "cadkit", "route", "--all"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        self.assertEqual(text.count("warning:"), sum(1 for r in routes.all_recommendations(DATA) if r["warnings"]))
        bad = subprocess.run([sys.executable, "-m", "cadkit", "route", "--input", "volume"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
