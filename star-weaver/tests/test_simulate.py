import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simulate  # noqa: E402


class SimulatorTests(unittest.TestCase):
    def test_skill_report_baseline(self):
        rep = simulate.skill_report(horizon=20)
        self.assertEqual(rep["legal_builds"], 6)
        for row in rep["build_summary"]:
            self.assertEqual(row["best_beacons"], 2)
            self.assertEqual(row["leftover_growth"], 0)
        aborted = [r for r in rep["runs"] if r["disruption"] != "none"]
        self.assertTrue(all(r["beacons"] <= 1 for r in aborted))

    def test_lineage_report_deterministic_and_grants_nothing(self):
        a = simulate.lineage_report(runs=3, generations=3, population=3, seed="t")
        b = simulate.lineage_report(runs=3, generations=3, population=3, seed="t")
        self.assertEqual(json.dumps(a, sort_keys=True, default=list),
                         json.dumps(b, sort_keys=True, default=list))
        self.assertEqual(a["status"], "EXPERIMENTAL")
        self.assertEqual(a["errors"], {})

    def test_simulator_does_not_write_data(self):
        before = {p: p.read_bytes() for p in (ROOT / "data").glob("*.json")}
        simulate.lineage_report(runs=1, generations=2, population=2, seed="w")
        self.assertEqual(before, {p: p.read_bytes() for p in (ROOT / "data").glob("*.json")})


if __name__ == "__main__":
    unittest.main()
