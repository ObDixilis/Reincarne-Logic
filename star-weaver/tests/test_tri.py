"""Automated unit and integration test suite for Star Weaver v0.3 (EXPERIMENTAL)."""
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starweaver.tri.engine import TriModel, load_tree, migrate_v02
from starweaver.tri.heredity import (
    catalog,
    founder_profiles,
    load_rules,
    make_child,
    validate_rules,
)
from starweaver.tri.ecosystem import audit_founder_symmetry, run_ecosystem
from starweaver.tri.simulate_tri import play_tri_build, skill_analysis_v3


class TestTriEngine(unittest.TestCase):
    def setUp(self):
        self.tree = load_tree()

    def test_tree_validation(self):
        self.assertEqual(len(self.tree["nodes"]), 22)
        self.assertEqual(self.tree["schema_version"], "0.3.0")
        self.assertEqual(self.tree["status"], "EXPERIMENTAL")

    def test_learn_progression_and_budget(self):
        m = TriModel(self.tree)
        self.assertEqual(m.state["growth_points"], 15)

        # Tier 0 practices
        self.assertEqual(m.learn("M0", "l-1"), "LEARNED")
        self.assertEqual(m.learn("T0", "l-2"), "LEARNED")
        self.assertEqual(m.learn("F0", "l-3"), "LEARNED")
        self.assertEqual(m.state["growth_points"], 12)

        # Tier 1 expressions
        self.assertEqual(m.learn("A1", "l-4"), "LEARNED")
        self.assertEqual(m.learn("T1", "l-5"), "LEARNED")
        self.assertEqual(m.learn("F1", "l-6"), "LEARNED")
        self.assertEqual(m.state["growth_points"], 9)

        # Compositions
        self.assertEqual(m.learn("H1", "l-7"), "LEARNED")
        self.assertEqual(m.learn("H2", "l-8"), "LEARNED")
        self.assertEqual(m.learn("H3", "l-9"), "LEARNED")
        self.assertEqual(m.state["growth_points"], 3)

        # Capstone Triune Weave requires 3 GP and H1, H2, H3
        self.assertEqual(m.learn("H4", "l-10"), "LEARNED")
        self.assertEqual(m.state["growth_points"], 0)

        # Over budget
        self.assertEqual(m.learn("A2", "l-11"), "POINTS")

    def test_mutual_exclusion(self):
        m = TriModel(self.tree)
        m.learn("M0", "l-1")
        m.learn("A1", "l-2")
        m.learn("A2", "l-3")

        # Learn A3a (burst)
        self.assertEqual(m.learn("A3a", "l-4"), "LEARNED")
        # Attempting A3b must be EXCLUDED
        self.assertEqual(m.learn("A3b", "l-5"), "EXCLUDED")

    def test_passives_and_regen(self):
        m = TriModel(self.tree)
        # Standard caps: 6/6/6
        self.assertEqual(m.caps()["focus"], 6)

        # Learn up to A3b (Sanctum Glow: +1 regen focus, +2 cap focus)
        m.learn("M0", "l-1")
        m.learn("A1", "l-2")
        m.learn("A2", "l-3")
        m.learn("A3b", "l-4")

        self.assertEqual(m.caps()["focus"], 8)
        self.assertEqual(m.regen()["focus"], 2)

        # Advance ticks to verify regen
        m.state["resources"]["focus"] = 2
        m.advance(3)  # interval is 3
        self.assertEqual(m.state["resources"]["focus"], 4)

    def test_coupling_abort(self):
        m = TriModel(self.tree)
        m.learn("M0", "l-1")
        m.learn("T0", "l-2")
        m.learn("A1", "l-3")
        m.learn("T1", "l-4")
        m.learn("H1", "l-5")

        # Activate H1
        self.assertEqual(m.activate("H1", "act-1"), "STARTED")
        # Cut Techfinity access during execution
        m.set_axis("Techfinity", "unavailable")
        self.assertIsNone(m.state["active"])
        self.assertEqual(m.state["events"][-1]["event"], "ABORTED")

    def test_save_and_restore(self):
        m = TriModel(self.tree)
        m.learn("M0", "l-1")
        m.learn("T0", "l-2")
        m.learn("A1", "l-3")

        raw = m.save()
        restored = TriModel.restore(self.tree, raw)
        self.assertEqual(restored.state["learned"], ["M0", "T0", "A1"])
        self.assertEqual(restored.state["growth_points"], m.state["growth_points"])

    def test_v02_migration(self):
        # A mock v0.2 save state
        v02_save = json.dumps({
            "schema_version": "0.1.0",
            "mechanics_digest": "mock-digest",
            "tick": 4,
            "growth_points": 0,
            "resources": {"focus": 2, "charge": 2},
            "axis_access": {"Affinity": "available", "Techfinity": "available"},
            "equipment": ["lamp"],
            "ranks": {"M0": 1, "T0": 1, "A1": 1, "T1": 1, "H1": 1},
            "spent": {"M0": [1], "T0": [1], "A1": [1], "T1": [1], "H1": [2]},
            "outputs": [{"tick": 2, "node": "H1", "output": "encoded_light_beacon", "request_id": "r1"}],
            "active": None,
        })

        migrated = migrate_v02(v02_save, self.tree)
        self.assertEqual(migrated.state["learned"], ["M0", "T0", "A1", "T1", "H1"])
        self.assertEqual(migrated.state["axis_access"]["Finity"], "available")
        self.assertEqual(migrated.state["resources"]["resonance"], 4)
        self.assertEqual(migrated.state["resources"]["focus"], 2)
        self.assertEqual(migrated.state["events"][-1]["event"], "MIGRATED_FROM_0.2")


class TestTriHeredity(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()
        self.founders = founder_profiles(self.rules)

    def test_rules_mirror_symmetry(self):
        # Must validate without raising ValueError
        validate_rules(self.rules)

    def test_child_reproducibility(self):
        p1 = self.founders["affinity-potential"]
        p2 = self.founders["techfinity-potential"]
        c1 = make_child(self.rules, p1, p2, seed="seed-xyz", route="biological")
        c2 = make_child(self.rules, p1, p2, seed="seed-xyz", route="biological")
        self.assertEqual(json.dumps(c1, sort_keys=True), json.dumps(c2, sort_keys=True))

    def test_emergence_and_hybrids(self):
        cat = catalog(self.rules)
        # High dual potential parents
        p1 = {"id": "p1", "generation": 0, "founders": ["p1"], "route": None, "seed": None,
              "potential": {"Affinity": 70.0, "Techfinity": 65.0, "Finity": 65.0}, "polarity": 0.0,
              "traits": [{"id": "starlit-blood", "origin": "founder", "dormant": False, "from": []},
                         {"id": "steady-hands", "origin": "founder", "dormant": False, "from": []}],
              "status": "EXPERIMENTAL", "learned_skills": [], "active_axis_access": {}}
        p2 = {"id": "p2", "generation": 0, "founders": ["p2"], "route": None, "seed": None,
              "potential": {"Affinity": 65.0, "Techfinity": 70.0, "Finity": 70.0}, "polarity": 0.0,
              "traits": [{"id": "circuit-blood", "origin": "founder", "dormant": False, "from": []},
                         {"id": "steady-hands", "origin": "founder", "dormant": False, "from": []}],
              "status": "EXPERIMENTAL", "learned_skills": [], "active_axis_access": {}}

        # Make child with deterministic seed
        child = make_child(self.rules, p1, p2, seed="triune-test-1", route="biological", cat=cat)
        origins = {t["origin"] for t in child["traits"]}
        self.assertTrue(len(child["traits"]) > 0)
        self.assertTrue(origins.intersection({"inherited", "emergent", "hybrid"}))

    def test_founder_symmetry_audit(self):
        audit = audit_founder_symmetry(self.rules, iterations=300, seed="test-audit")
        self.assertTrue(audit["symmetry_verified"])
        self.assertLess(audit["axis_discrepancy"], 1.5)


class TestTriEcosystem(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_ecosystem_drift(self):
        eco = run_ecosystem(self.rules, generations=4, carrying_capacity=16, seed="test-eco", niche_id="crossroads")
        self.assertEqual(len(eco["history"]), 4)
        self.assertGreater(eco["discovery_catalog"]["total_discovered"], 0)


if __name__ == "__main__":
    unittest.main()
