"""Behavior checks for experimental succession, validation, and ancestor replay."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from starweaver.heredity import (
    CHANNELS, LineageError, extend_catalog, generate_lineage, load_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


class HeredityTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(ROOT / "data")

    def generate(self, first="affinity-potential", second="techfinity-potential", seed="trial-1"):
        return generate_lineage(self.catalog, first, second, seed)

    def test_catalog_contains_all_four_provenance_channels_and_eight_synthetic_profiles(self):
        self.assertEqual(len(self.catalog["profiles"]), 8)
        self.assertEqual({trait["channel"] for trait in self.catalog["traits"]}, set(CHANNELS))
        self.assertEqual(self.catalog["rules"]["status"], "EXPERIMENTAL")
        self.assertTrue(all(profile["generation"] == 0 and profile["source_lineage"] is None
                            for profile in self.catalog["profiles"]))

    def test_fixed_seed_is_repeatable_across_copies_and_disk_reads(self):
        first = self.generate()
        second = generate_lineage(load_catalog(ROOT / "data"), "affinity-potential", "techfinity-potential", "trial-1")
        self.assertEqual(first, second)
        self.assertEqual(first["id"], "lineage-a2be071d5c4f750d7c0d")
        self.assertEqual([trait["id"] for trait in first["traits"]],
                         ["trait-affinity-biological", "trait-interface-blueprint"])

    def test_seed_changes_a_real_transmission_outcome(self):
        self.assertNotEqual(self.generate(seed="trial-0")["traits"], self.generate(seed="trial-1")["traits"])

    def test_reciprocal_cross_preserves_trait_outcome_but_records_parent_order(self):
        first = self.generate()
        second = self.generate("techfinity-potential", "affinity-potential")
        self.assertEqual([trait["id"] for trait in first["traits"]], [trait["id"] for trait in second["traits"]])
        self.assertEqual(first["axis_potential"], second["axis_potential"])
        self.assertEqual(second["parent_ids"], list(reversed(first["parent_ids"])))
        self.assertNotEqual(first["id"], second["id"])

    def test_zero_axis_teaching_and_blueprint_cross_can_offer_ordinary_interaction(self):
        result = self.generate("archive-keeper", "ordinary-learner", "trial-1")
        self.assertEqual(result["axis_potential"], {"Affinity": False, "Techfinity": False})
        ordinary = next(branch for branch in result["branches"] if branch["id"] == "interaction-ordinary-methods")
        self.assertEqual(ordinary["status"], "CANDIDATE")
        self.assertEqual(ordinary["requires_potential"], [])
        self.assertEqual(result["branches"][0]["skill_candidates"], ["M0", "T0"])

    def test_one_axis_hybrid_retains_ordinary_technology_boundary(self):
        result = self.generate("affinity-potential", "fabricated-successor", "trial-0")
        self.assertEqual(result["axis_potential"], {"Affinity": True, "Techfinity": False})
        branches = {branch["id"]: branch for branch in result["branches"]}
        self.assertEqual(branches["interaction-affinity-device"]["status"], "CANDIDATE")
        self.assertEqual(branches["interaction-independent-expressions"]["status"], "BLOCKED")
        self.assertIn("potential:Techfinity", branches["interaction-independent-expressions"]["missing"])

    def test_two_axis_candidate_suggests_beacon_without_granting_it(self):
        result = self.generate()
        self.assertEqual(result["axis_potential"], {"Affinity": True, "Techfinity": True})
        self.assertIn("H1", result["branches"][0]["skill_candidates"])
        self.assertEqual(result["learned_skills"], [])
        self.assertEqual(result["active_axis_access"], {"Affinity": "unavailable", "Techfinity": "unavailable"})
        self.assertNotIn("equipment", result)
        self.assertNotIn("resources", result)

    def test_every_inherited_trait_names_real_parent_trait_and_founder(self):
        result = self.generate(seed="trial-5")
        profiles = {profile["id"]: profile for profile in self.catalog["profiles"]}
        for trait in result["traits"]:
            provenance = trait["provenance"]
            self.assertTrue(provenance["parent_references"])
            for source in provenance["parent_references"]:
                self.assertIn(source["profile_id"], result["parent_ids"])
                self.assertIn(source["trait_id"], profiles[source["profile_id"]]["traits"])
                self.assertEqual(source["generation"], 0)
            for source in provenance["founder_origins"]:
                self.assertIn(source["trait_id"], profiles[source["profile_id"]]["traits"])
                self.assertEqual(source["channel"], trait["channel"])

    def test_absent_traits_cannot_spontaneously_appear(self):
        result = self.generate("archive-keeper", "ordinary-learner", "trial-1")
        parents = [profile for profile in self.catalog["profiles"] if profile["id"] in result["parent_ids"]]
        allowed = set().union(*(set(profile["traits"]) for profile in parents))
        self.assertTrue({trait["id"] for trait in result["traits"]}.issubset(allowed))
        for step in result["trace"]:
            if not step["parent_ids"]:
                self.assertIsNone(step["draw"])
                self.assertFalse(step["inherited"])

    def test_both_parent_policy_is_distinct_and_trace_is_inspectable(self):
        result = self.generate("archive-keeper", "ordinary-learner", "trial-0")
        step = next(step for step in result["trace"] if step["trait_id"] == "trait-spell-mentorship")
        self.assertEqual(step["parent_ids"], ["archive-keeper", "ordinary-learner"])
        self.assertEqual((step["numerator"], step["denominator"], step["draw"]), (1, 1, 0))
        self.assertTrue(step["inherited"])
        self.assertEqual(len(result["trace"]), len(self.catalog["traits"]))

    def test_generation_and_extension_never_mutate_inputs(self):
        before = copy.deepcopy(self.catalog)
        lineage = self.generate()
        snapshot = copy.deepcopy(lineage)
        extended = extend_catalog(self.catalog, lineage)
        self.assertEqual(self.catalog, before)
        self.assertEqual(lineage, snapshot)
        self.assertEqual(len(extended["profiles"]), len(self.catalog["profiles"]) + 1)
        extended["profiles"][-1]["traits"].clear()
        self.assertEqual(lineage, snapshot)

    def test_registration_is_idempotent_and_returns_a_copy(self):
        lineage = self.generate()
        extended = extend_catalog(self.catalog, lineage)
        again = extend_catalog(extended, lineage)
        self.assertEqual(extended, again)
        self.assertIsNot(extended, again)

    def test_multigeneration_preserves_immediate_and_founder_provenance(self):
        first = self.generate(seed="trial-1")
        extended = extend_catalog(self.catalog, first)
        second = generate_lineage(extended, first["id"], "archive-keeper", "generation-two")
        self.assertEqual(second["generation"], 2)
        self.assertTrue({first["id"], "affinity-potential", "techfinity-potential", "archive-keeper"}
                        .issubset(second["ancestry"]))
        inherited_from_first = [trait for trait in second["traits"]
                                if any(source["profile_id"] == first["id"]
                                       for source in trait["provenance"]["parent_references"])]
        self.assertTrue(inherited_from_first)
        for trait in inherited_from_first:
            self.assertTrue(any(origin["profile_id"] in {"affinity-potential", "techfinity-potential"}
                                for origin in trait["provenance"]["founder_origins"]))
            self.assertTrue(any(source["source_lineage_id"] == first["id"] and source["generation"] == 1
                                for source in trait["provenance"]["parent_references"]))
        self.assertEqual(second["learned_skills"], [])
        self.assertTrue(all(value == "unavailable" for value in second["active_axis_access"].values()))
        # Generation snapshots remain flat: registry profiles own snapshots, but
        # no output embeds a parent profile or nested ancestor snapshot.
        self.assertNotIn('"source_lineage":', json.dumps(second))
        self.assertEqual(generate_lineage(extended, first["id"], "archive-keeper", "generation-two"), second)

    def test_two_generated_parents_merge_founder_origins_without_duplicates(self):
        first = self.generate(seed="trial-5")
        catalog = extend_catalog(self.catalog, first)
        other = generate_lineage(catalog, "affinity-potential", "techfinity-potential", "trial-7")
        catalog = extend_catalog(catalog, other)
        child = generate_lineage(catalog, first["id"], other["id"], "merged-origins")
        self.assertEqual(child["generation"], 2)
        for trait in child["traits"]:
            origins = trait["provenance"]["founder_origins"]
            self.assertEqual(len(origins), len({json.dumps(origin, sort_keys=True) for origin in origins}))

    def test_unknown_parent_and_self_succession_are_rejected(self):
        for first, second in [("unknown-profile", "archive-keeper"), ("archive-keeper", "archive-keeper")]:
            with self.subTest(first=first, second=second), self.assertRaises(LineageError):
                self.generate(first, second)

    def test_nontext_empty_control_and_oversized_seeds_are_rejected(self):
        for seed in [None, True, 123, "", "   ", "x\ny", "x" * 81, {}, []]:
            with self.subTest(seed=seed), self.assertRaises(LineageError):
                self.generate(seed=seed)

    def test_unicode_seed_is_supported_and_repeatable(self):
        self.assertEqual(self.generate(seed="étoile-星"), self.generate(seed="étoile-星"))

    def test_unknown_fields_and_axes_cannot_add_a_gameplay_hierarchy(self):
        altered = copy.deepcopy(self.catalog)
        altered["traits"][0]["axis"] = "Finity"
        with self.assertRaises(LineageError):
            generate_lineage(altered, "archive-keeper", "ordinary-learner", "test")
        altered = copy.deepcopy(self.catalog)
        altered["rules"]["parent_system"] = "Finity"
        with self.assertRaises(LineageError):
            generate_lineage(altered, "archive-keeper", "ordinary-learner", "test")

    def test_invalid_policy_fractions_and_boolean_numbers_are_rejected(self):
        for fraction in [{"numerator": 2, "denominator": 1}, {"numerator": True, "denominator": 2},
                         {"numerator": 1, "denominator": 0}, {"numerator": 1, "denominator": 1001}]:
            altered = copy.deepcopy(self.catalog)
            altered["rules"]["channels"]["biological"]["single_parent"] = fraction
            with self.subTest(fraction=fraction), self.assertRaises(LineageError):
                generate_lineage(altered, "affinity-potential", "techfinity-potential", "test")

    def test_teaching_cannot_be_promoted_to_axis_potential(self):
        altered = copy.deepcopy(self.catalog)
        trait = next(trait for trait in altered["traits"] if trait["channel"] == "cultural_mentorship")
        trait["axis"], trait["meaning"] = "Affinity", "potential"
        with self.assertRaises(LineageError):
            generate_lineage(altered, "archive-keeper", "ordinary-learner", "test")

    def test_catalog_references_duplicates_and_type_errors_are_rejected(self):
        alterations = [
            lambda c: c["profiles"].append(copy.deepcopy(c["profiles"][0])),
            lambda c: c["traits"].append(copy.deepcopy(c["traits"][0])),
            lambda c: c["profiles"][0]["traits"].append("missing-trait"),
            lambda c: c["profiles"][0].update(generation=True),
            lambda c: c["traits"][0].update(meaning=[]),
            lambda c: c["rules"].update(status="CANON"),
        ]
        for alteration in alterations:
            altered = copy.deepcopy(self.catalog)
            alteration(altered)
            with self.subTest(alteration=alteration), self.assertRaises(LineageError):
                generate_lineage(altered, "archive-keeper", "ordinary-learner", "test")

    def test_registration_rejects_modified_potential_ranks_access_or_provenance(self):
        first = self.generate()
        alterations = [
            lambda v: v["axis_potential"].update(Affinity=False),
            lambda v: v["learned_skills"].append("H1"),
            lambda v: v["active_axis_access"].update(Affinity="available"),
            lambda v: v["traits"][0]["provenance"]["founder_origins"][0].update(profile_id="archive-keeper"),
            lambda v: v.update(equipment=["lamp"]),
            lambda v: v.update(generation=True),
        ]
        for alteration in alterations:
            altered = copy.deepcopy(first)
            alteration(altered)
            with self.subTest(alteration=alteration), self.assertRaises(LineageError):
                extend_catalog(self.catalog, altered)

    def test_altered_registered_profile_cannot_bypass_snapshot_validation(self):
        extended = extend_catalog(self.catalog, self.generate())
        extended["profiles"][-1]["traits"].append("trait-spell-mentorship")
        with self.assertRaises(LineageError):
            generate_lineage(extended, extended["profiles"][-1]["id"], "archive-keeper", "test")

    def test_cycle_or_unknown_parent_snapshot_is_rejected(self):
        lineage = self.generate()
        lineage["parent_ids"][0] = lineage["id"]
        with self.assertRaises(LineageError):
            extend_catalog(self.catalog, lineage)

    def test_forward_references_are_rejected_and_ordered_replay_succeeds(self):
        first = self.generate()
        extended = extend_catalog(self.catalog, first)
        second = generate_lineage(extended, first["id"], "archive-keeper", "generation-two")
        extended = extend_catalog(extended, second)
        reordered = copy.deepcopy(extended)
        reordered["profiles"][-2:] = list(reversed(reordered["profiles"][-2:]))
        with self.assertRaises(LineageError):
            generate_lineage(reordered, second["id"], "ordinary-learner", "next")
        self.assertEqual(generate_lineage(extended, second["id"], "ordinary-learner", "next")["generation"], 3)

    def test_catalog_rejects_too_many_profiles_before_generating(self):
        self.catalog["profiles"] *= 17
        with self.assertRaises(LineageError):
            self.generate()

    def test_thirty_generation_registry_bound_and_snapshot_size_stay_bounded(self):
        catalog = self.catalog
        parent_id = "affinity-potential"
        for generation in range(1, 31):
            lineage = generate_lineage(catalog, parent_id, "archive-keeper", f"bounded-{generation}")
            catalog = extend_catalog(catalog, lineage)
            self.assertEqual(lineage["generation"], generation)
            self.assertLess(len(json.dumps(lineage)), 30_000)
            parent_id = lineage["id"]
        with self.assertRaises(LineageError):
            generate_lineage(catalog, parent_id, "archive-keeper", "too-deep")
        fresh = generate_lineage(catalog, "ordinary-learner", "fabricated-successor", "too-many")
        with self.assertRaises(LineageError):
            extend_catalog(catalog, fresh)

    def test_duplicate_json_fields_and_oversized_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lineages.json"
            path.write_text('{"profiles":[],"profiles":[],"traits":[],"rules":{}}', encoding="utf-8")
            with self.assertRaises(LineageError):
                load_catalog(Path(directory))
            path.write_text("x" * 1_048_577, encoding="utf-8")
            with self.assertRaises(LineageError):
                load_catalog(Path(directory))

    def test_bad_encoding_and_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lineages.json"
            for data in [b"\xff\xfe", b"{broken"]:
                path.write_bytes(data)
                with self.subTest(data=data), self.assertRaises(LineageError):
                    load_catalog(Path(directory))

    def test_rejected_registration_preserves_original_catalog(self):
        original = copy.deepcopy(self.catalog)
        lineage = self.generate()
        lineage["trace"][0]["inherited"] = not lineage["trace"][0]["inherited"]
        with self.assertRaises(LineageError):
            extend_catalog(self.catalog, lineage)
        self.assertEqual(self.catalog, original)

    def test_public_output_roundtrips_as_plain_json(self):
        result = self.generate()
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_checked_in_pathway_examples_reproduce_and_replay(self):
        packet = json.loads((ROOT / "data" / "hereditary-pathways.json").read_text(encoding="utf-8"))
        for example in packet["cases"]:
            lineage = example["lineage"]
            with self.subTest(case=example["case_id"]):
                self.assertEqual(generate_lineage(self.catalog, *lineage["parent_ids"], lineage["seed"]), lineage)
        catalog = self.catalog
        for snapshot in packet["multigeneration"]["registration_order"]:
            self.assertEqual(generate_lineage(catalog, *snapshot["parent_ids"], snapshot["seed"]), snapshot)
            catalog = extend_catalog(catalog, snapshot)
        self.assertEqual(catalog["profiles"][-1]["generation"], 2)


if __name__ == "__main__":
    unittest.main()
