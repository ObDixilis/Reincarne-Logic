"""Unit and integration tests for Star Weaver v0.3.1 Manifestation Compiler (EXPERIMENTAL)."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starweaver.tri.engine import TriModel, load_tree
from starweaver.tri.heredity import founder_profiles, load_rules, make_child
from starweaver.tri.manifestation import (
    ManifestationCompiler,
    compile_woven_beacon_vertical_slice,
    load_manifestation_catalog,
    validate_manifestation_catalog,
)


class TestManifestationCompiler(unittest.TestCase):
    def setUp(self):
        self.catalog = load_manifestation_catalog()
        self.compiler = ManifestationCompiler(self.catalog)

    def test_catalog_validation(self):
        validate_manifestation_catalog(self.catalog)
        self.assertEqual(self.catalog["schema_version"], "0.3.1")
        self.assertEqual(self.catalog["status"], "EXPERIMENTAL")

    def test_7_anchor_color_gamut_and_skin_safe_luminance(self):
        gamut = self.catalog["color_gamut"]
        required_anchors = ["magenta", "cyan", "lemon_lime", "solar_amber", "red_orange", "threshold_uv", "void_black"]
        for anchor in required_anchors:
            self.assertIn(anchor, gamut)
            entry = gamut[anchor]
            self.assertTrue(entry["hex"].startswith("#"))
            # Luminance must be bounded for skin safety (maximum 500 nits to preserve Black skin contrast)
            self.assertLessEqual(entry["skin_safe_max_luminance_nits"], 500.0)

    def test_line_grammar_three_modes(self):
        grammar = self.catalog["line_grammar_rules"]
        self.assertEqual(grammar["wave"]["mode"], "continuous")
        self.assertEqual(grammar["particle"]["mode"], "discrete")
        self.assertEqual(grammar["zigzag"]["mode"], "routed")

    def test_material_channel_taxonomy(self):
        channels = self.catalog["material_channels"]
        self.assertIn("Aetherwear", channels)
        self.assertIn("Assorcery", channels)
        self.assertIn("Ordinary", channels)
        self.assertIn("Inherent", channels)

    def test_woven_beacon_vertical_slice_normal(self):
        slice_result = compile_woven_beacon_vertical_slice(equipment=["lamp"], drop_lamp=False)
        normal = slice_result["normal_execution"]

        self.assertEqual(normal["skill_id"], "H1")
        self.assertEqual(normal["status"], "ACTIVE")
        self.assertEqual(normal["material_channel"], "Assorcery")
        self.assertEqual(normal["apparatus_required"], ["lamp"])

        # Must combine continuous wave carrier and routed zigzag modulation
        grammar_kinds = [g["kind"] for g in normal["line_grammar"]]
        self.assertIn("wave", grammar_kinds)
        self.assertIn("zigzag", grammar_kinds)

        # Dual-braid color palette: Sorcery Magenta (#FF2BD6) + Precision Cyan (#00E5FF)
        hex_colors = [c["hex"] for c in normal["visual_palette"]]
        self.assertIn("#FF2BD6", hex_colors)
        self.assertIn("#00E5FF", hex_colors)

        # World effect must be an addressed encoded light beacon
        world = normal["world_effect"]
        self.assertEqual(world["kind"], "encoded_light_beacon")
        self.assertEqual(world["signal_protocol"], "woven_carrier_protocol_v1")
        # Physical range and collision profile deliberately left unquantified pending canon physics
        self.assertIsNone(world["range_meters"])
        self.assertIsNone(world["collision_profile"])
        self.assertEqual(world["persistence_ticks"], 2)

        # Skin tone protection check
        self.assertIn("melanin", normal["skin_tone_protection_rule"].lower())

    def test_woven_beacon_vertical_slice_interrupted(self):
        slice_result = compile_woven_beacon_vertical_slice(equipment=["lamp"], drop_lamp=True)
        interrupted = slice_result["interrupted_execution"]

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        self.assertEqual(interrupted["apparatus_present"], [])
        self.assertIsNotNone(interrupted["failure_report"])
        self.assertIn("Dissolve Lattice", interrupted["failure_report"]["breakdown_visual"])
        self.assertIn("HARDWARE_LOSS", interrupted["failure_report"]["reason"])
        self.assertEqual(interrupted["world_effect"]["persistence_ticks"], 0)

    def test_choreography_cultural_mentorship_influence(self):
        performer = {"mentorship_tradition": "Gorgon Flow Arts Lineage"}
        frame = self.compiler.compile(skill_id="H1", performer_profile=performer)
        self.assertIn("Gorgon Flow Arts Lineage Variation", frame.choreography["flow_style"])
        # World effect remains deterministically identical
        self.assertEqual(frame.world_effect["kind"], "encoded_light_beacon")

    def test_engine_integration_get_manifestation(self):
        tree = load_tree()
        m = TriModel(tree)
        m.learn("M0", "l-1")
        m.learn("T0", "l-2")
        m.learn("A1", "l-3")
        m.learn("T1", "l-4")
        m.learn("H1", "l-5")

        m.activate("H1", "act-1")
        frame = m.get_manifestation("H1")
        self.assertEqual(frame.status, "ACTIVE")
        self.assertEqual(frame.skill_id, "H1")
        self.assertIn("Assorcery", frame.material_channel)

        ascii_diagram = frame.render_ascii_diagram()
        self.assertIn("MAGENTA WAVE", ascii_diagram)
        self.assertIn("CYAN ZIGZAG", ascii_diagram)

    def test_triune_woven_heredity_vs_triune_weave_skill_distinction(self):
        rules = load_rules()
        cat = self.catalog
        # Triune-Woven is a hereditary trait requiring >=60 on all axes
        triune_trait = next((t for t in rules["hybrids"] if t["id"] == "triune-weave"), None)
        self.assertIsNotNone(triune_trait)
        self.assertEqual(triune_trait["min"]["Affinity"], 60)
        self.assertEqual(triune_trait["min"]["Techfinity"], 60)
        self.assertEqual(triune_trait["min"]["Finity"], 60)

        # Generating a child with Triune-Woven trait does NOT grant learned ranks
        p1 = {"id": "p1", "generation": 0, "founders": ["p1"], "route": None, "seed": None,
              "potential": {"Affinity": 75.0, "Techfinity": 75.0, "Finity": 75.0}, "polarity": 0.0,
              "traits": [], "status": "EXPERIMENTAL", "learned_skills": [], "active_axis_access": {}}
        p2 = {"id": "p2", "generation": 0, "founders": ["p2"], "route": None, "seed": None,
              "potential": {"Affinity": 75.0, "Techfinity": 75.0, "Finity": 75.0}, "polarity": 0.0,
              "traits": [], "status": "EXPERIMENTAL", "learned_skills": [], "active_axis_access": {}}
        child = make_child(rules, p1, p2, seed="seed-triune", route="biological")
        self.assertEqual(child["learned_skills"], [])
        self.assertEqual(child["active_axis_access"]["Affinity"], "unavailable")

        # But Triune Weave (H4) is a learned capstone in tree.json requiring H1, H2, H3
        tree = load_tree()
        h4_node = next(n for n in tree["nodes"] if n["id"] == "H4")
        self.assertEqual(h4_node["kind"], "capstone")
        self.assertEqual(h4_node["requires"], ["H1", "H2", "H3"])


if __name__ == "__main__":
    unittest.main()
