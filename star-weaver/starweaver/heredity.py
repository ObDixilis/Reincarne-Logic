"""Bounded experimental provenance routes; no skill or active access inheritance.

The deterministic hash gates are fixture policies, not genetic probabilities or
canonical rules. All public functions reject malformed or altered snapshots.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

AXES = ("Affinity", "Techfinity")
CHANNELS = (
    "biological",
    "resonant",
    "cultural_mentorship",
    "fabricated_blueprint",
)
MAX_GENERATIONS = 30
MAX_PROFILES = 128
MAX_TRAITS = 24
MAX_CATALOG_BYTES = 1_048_576
MAX_SNAPSHOT_BYTES = 262_144
_ID = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")
_SKILLS = {"M0", "T0", "A1", "T1", "H1"}


class LineageError(ValueError):
    """An invalid lineage request, catalog, or unverified generation snapshot."""


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise LineageError("Value must be finite, acyclic JSON data.") from exc


def _closed(value: object, keys: set[str], where: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise LineageError(f"{where} must contain exactly: {', '.join(sorted(keys))}.")
    return value


def _text(value: object, where: str, maximum: int = 600) -> str:
    if (type(value) is not str or not 1 <= len(value) <= maximum
            or not value.strip() or not value.isprintable()):
        raise LineageError(f"{where} must be printable text, 1-{maximum} characters.")
    return value


def _identifier(value: object, where: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise LineageError(f"{where} must be a lowercase ID of at most 80 characters.")
    return value


def _items(value: object, where: str, maximum: int, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise LineageError(f"{where} must be a list containing {minimum}-{maximum} items.")
    return value


def _unique_ids(value: object, where: str, maximum: int,
                allowed: set[str] | None = None) -> list[str]:
    values = _items(value, where, maximum)
    for item in values:
        if allowed is None:
            _identifier(item, where)
        elif type(item) is not str or item not in allowed:
            raise LineageError(f"{where} contains an unknown reference.")
    if len(set(values)) != len(values):
        raise LineageError(f"{where} must not contain duplicate references.")
    return values


def _fraction(value: object, where: str) -> None:
    pair = _closed(value, {"numerator", "denominator"}, where)
    numerator, denominator = pair["numerator"], pair["denominator"]
    if (type(numerator) is not int or type(denominator) is not int
            or not 1 <= denominator <= 1000 or not 0 <= numerator <= denominator):
        raise LineageError(f"{where} must be an integer fraction between zero and one.")


def _mechanics_digest(catalog: dict) -> str:
    value = {"traits": catalog["traits"], "rules": catalog["rules"]}
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


def _profile_from_lineage(lineage: dict) -> dict:
    return {
        "id": lineage["id"],
        "label": f"Generation {lineage['generation']} · {lineage['id'][-8:]}",
        "description": "Registered experimental generation; potential and provenance only.",
        "traits": [trait["id"] for trait in lineage["traits"]],
        "generation": lineage["generation"],
        "source_lineage": copy.deepcopy(lineage),
    }


def _validate_catalog(catalog: object) -> dict:
    root = _closed(catalog, {"profiles", "traits", "rules"}, "Catalog")
    # Bound aggregate work before replaying snapshots. Python callers must also
    # provide JSON-safe input, rather than objects with custom equality methods.
    if len(_canonical(root).encode("ascii")) > 4 * MAX_CATALOG_BYTES:
        raise LineageError("Expanded catalog exceeds its size limit.")
    traits = _items(root["traits"], "Catalog traits", MAX_TRAITS, 1)
    trait_ids: set[str] = set()
    for trait in traits:
        _closed(trait, {"id", "label", "channel", "axis", "description", "meaning"}, "Trait")
        trait_id = _identifier(trait["id"], "Trait ID")
        if trait_id in trait_ids:
            raise LineageError("Duplicate trait ID.")
        trait_ids.add(trait_id)
        _text(trait["label"], "Trait label", 120)
        _text(trait["description"], "Trait description")
        if trait["channel"] not in CHANNELS:
            raise LineageError("Unknown transmission channel.")
        if trait["axis"] is not None and trait["axis"] not in AXES:
            raise LineageError("Trait axis must be Affinity, Techfinity, or null.")
        if trait["meaning"] not in ("potential", "teaching_pathway", "blueprint_pathway"):
            raise LineageError("Unknown trait meaning.")
        if trait["axis"] is not None and trait["meaning"] != "potential":
            raise LineageError("An axis-bearing trait must represent potential only.")
        if trait["channel"] == "cultural_mentorship" and (
                trait["axis"] is not None or trait["meaning"] != "teaching_pathway"):
            raise LineageError("Teaching pathways cannot inherit skill ranks or axis access.")

    rules = _closed(root["rules"], {"id", "status", "description", "channels", "interactions"}, "Rules")
    _text(rules["id"], "Ruleset ID", 80)
    if rules["status"] != "EXPERIMENTAL":
        raise LineageError("Inheritance rules must remain EXPERIMENTAL.")
    _text(rules["description"], "Rules description")
    _closed(rules["channels"], set(CHANNELS), "Channel policies")
    policy_ids: set[str] = set()
    for channel in CHANNELS:
        policy = _closed(rules["channels"][channel],
                         {"id", "single_parent", "both_parents", "description"}, "Channel policy")
        policy_id = _identifier(policy["id"], "Policy ID")
        if policy_id in policy_ids:
            raise LineageError("Duplicate policy ID.")
        policy_ids.add(policy_id)
        _text(policy["description"], "Policy description")
        _fraction(policy["single_parent"], "Single-parent policy")
        _fraction(policy["both_parents"], "Both-parent policy")
    interaction_ids: set[str] = set()
    for interaction in _items(rules["interactions"], "Interactions", 16):
        _closed(interaction, {"id", "label", "requires_traits", "requires_potential",
                              "skill_candidates", "recipe_pattern", "description"}, "Interaction")
        interaction_id = _identifier(interaction["id"], "Interaction ID")
        if interaction_id in interaction_ids:
            raise LineageError("Duplicate interaction ID.")
        interaction_ids.add(interaction_id)
        _text(interaction["label"], "Interaction label", 120)
        _text(interaction["description"], "Interaction description")
        _text(interaction["recipe_pattern"], "Recipe pattern", 120)
        _unique_ids(interaction["requires_traits"], "Interaction traits", MAX_TRAITS, trait_ids)
        _unique_ids(interaction["requires_potential"], "Interaction potential", 2, set(AXES))
        _unique_ids(interaction["skill_candidates"], "Candidate skills", 5, _SKILLS)

    profiles = _items(root["profiles"], "Profiles", MAX_PROFILES, 1)
    replay = {"traits": traits, "rules": rules, "profiles": []}
    profile_ids: set[str] = set()
    generated_count = 0
    for profile in profiles:
        _closed(profile, {"id", "label", "description", "traits", "generation", "source_lineage"}, "Profile")
        profile_id = _identifier(profile["id"], "Profile ID")
        if profile_id in profile_ids:
            raise LineageError("Duplicate profile ID.")
        profile_ids.add(profile_id)
        _text(profile["label"], "Profile label", 120)
        _text(profile["description"], "Profile description")
        _unique_ids(profile["traits"], "Profile traits", MAX_TRAITS, trait_ids)
        if type(profile["generation"]) is not int or not 0 <= profile["generation"] <= MAX_GENERATIONS:
            raise LineageError("Profile generation must be an integer from zero to thirty.")
        snapshot = profile["source_lineage"]
        if snapshot is None:
            if profile["generation"] != 0 or profile_id.startswith("lineage-"):
                raise LineageError("Generated parent profiles require a verified source snapshot.")
        else:
            generated_count += 1
            if generated_count > MAX_GENERATIONS:
                raise LineageError("The catalog permits at most thirty registered generations.")
            expected = _recompute_snapshot(replay, snapshot)
            if _canonical(profile) != _canonical(_profile_from_lineage(expected)):
                raise LineageError("Generated parent profile differs from its verified snapshot.")
        replay["profiles"].append(profile)
    return root


def _validate_request(catalog: dict, parent_a: object, parent_b: object,
                      seed: object) -> tuple[dict, dict, str]:
    _identifier(parent_a, "Parent A")
    _identifier(parent_b, "Parent B")
    if parent_a == parent_b:
        raise LineageError("Select two distinct parent profiles; self-succession is outside this fixture.")
    _text(seed, "Seed", 80)
    parents = {profile["id"]: profile for profile in catalog["profiles"]}
    if parent_a not in parents or parent_b not in parents:
        raise LineageError("Unknown, forward, or cyclic parent reference; register earlier generations first.")
    first, second = parents[parent_a], parents[parent_b]
    if max(first["generation"], second["generation"]) >= MAX_GENERATIONS:
        raise LineageError("A lineage cannot exceed generation thirty.")
    return first, second, seed


def _founders(profile: dict, trait_id: str, channel: str) -> list[dict]:
    snapshot = profile["source_lineage"]
    if snapshot is None:
        return [{"profile_id": profile["id"], "trait_id": trait_id, "channel": channel}]
    for trait in snapshot["traits"]:
        if trait["id"] == trait_id:
            return trait["provenance"]["founder_origins"]
    raise LineageError("Parent snapshot has no provenance for a declared trait.")


def _branches(catalog: dict, traits: list[dict], potential: dict) -> list[dict]:
    trait_ids = {trait["id"] for trait in traits}
    inherited_axes = [axis for axis in AXES if potential[axis]]
    candidates = ["M0", "T0"]
    if potential["Affinity"]:
        candidates.append("A1")
    if potential["Techfinity"]:
        candidates.append("T1")
    if all(potential.values()):
        candidates.append("H1")
    route_id = "branch-" + ("dual-potential" if len(inherited_axes) == 2 else
                            "affinity-potential" if potential["Affinity"] else
                            "techfinity-potential" if potential["Techfinity"] else "ordinary")
    result = [{
        "id": route_id,
        "label": {0: "Ordinary practice route", 1: "One-axis potential route", 2: "Two-axis potential route"}[len(inherited_axes)],
        "kind": "progression_route", "status": "CANDIDATE",
        "requires_traits": [], "requires_potential": inherited_axes,
        "missing": [], "skill_candidates": candidates,
        "recipe_pattern": "Independent practice and expression progression",
        "description": "Suggestions only. Growth, training, equipment, and independently supplied axis access are still required.",
    }]
    for interaction in catalog["rules"]["interactions"]:
        missing = (["trait:" + item for item in interaction["requires_traits"] if item not in trait_ids]
                   + ["potential:" + axis for axis in interaction["requires_potential"] if not potential[axis]])
        result.append({**copy.deepcopy(interaction), "kind": "cross_channel_interaction",
                       "status": "BLOCKED" if missing else "CANDIDATE", "missing": missing})
    return result


def _generate_validated(catalog: dict, parent_a: str, parent_b: str, seed: str) -> dict:
    first, second, seed = _validate_request(catalog, parent_a, parent_b, seed)
    mechanics_digest = _mechanics_digest(catalog)
    # Sort the parent payload for symmetric outcomes; keep requested slot order
    # in parent_ids and immediate provenance for an inspectable reciprocal cross.
    context = {"ruleset_digest": mechanics_digest, "seed": seed,
               "parents": sorted((first, second), key=lambda value: value["id"])}
    context_text = _canonical(context)
    identity = {"context": context, "parent_ids": [parent_a, parent_b]}
    lineage_id = "lineage-" + hashlib.sha256(_canonical(identity).encode("ascii")).hexdigest()[:20]
    inherited: list[dict] = []
    trace: list[dict] = []
    for trait in sorted(catalog["traits"], key=lambda value: value["id"]):
        contributors = [parent for parent in (first, second) if trait["id"] in parent["traits"]]
        policy = catalog["rules"]["channels"][trait["channel"]]
        fraction = policy["both_parents" if len(contributors) == 2 else "single_parent"]
        denominator, numerator = fraction["denominator"], fraction["numerator"]
        draw = (int.from_bytes(hashlib.sha256((context_text + "|" + trait["id"]).encode("ascii")).digest(), "big")
                % denominator) if contributors else None
        selected = bool(contributors) and draw < numerator
        trace.append({"trait_id": trait["id"], "channel": trait["channel"],
                      "parent_ids": [parent["id"] for parent in contributors],
                      "policy_id": policy["id"], "numerator": numerator,
                      "denominator": denominator, "draw": draw, "inherited": selected,
                      "reason": "Passed the deterministic fixture gate." if selected else
                                "No contributing parent; no spontaneous trait." if not contributors else
                                "Did not pass the deterministic fixture gate."})
        if not selected:
            continue
        founder_map = {}
        for parent in contributors:
            for origin in _founders(parent, trait["id"], trait["channel"]):
                founder_map[_canonical(origin)] = origin
        inherited.append({**copy.deepcopy(trait), "provenance": {
            "policy_id": policy["id"],
            "parent_references": [{"profile_id": parent["id"], "trait_id": trait["id"],
                                   "generation": parent["generation"],
                                   "source_lineage_id": None if parent["source_lineage"] is None else parent["source_lineage"]["id"]}
                                  for parent in contributors],
            "founder_origins": [copy.deepcopy(founder_map[key]) for key in sorted(founder_map)],
        }})
    potential = {axis: any(trait["axis"] == axis for trait in inherited) for axis in AXES}
    ancestors: set[str] = set()
    for parent in (first, second):
        ancestors.add(parent["id"])
        if parent["source_lineage"] is not None:
            ancestors.update(parent["source_lineage"]["ancestry"])
    return {
        "id": lineage_id, "parent_ids": [parent_a, parent_b], "seed": seed,
        "ruleset_id": catalog["rules"]["id"], "ruleset_digest": mechanics_digest,
        "status": "EXPERIMENTAL", "generation": max(first["generation"], second["generation"]) + 1,
        "ancestry": sorted(ancestors), "traits": inherited,
        "axis_potential": potential, "learned_skills": [],
        "active_axis_access": {axis: "unavailable" for axis in AXES},
        "branches": _branches(catalog, inherited, potential), "trace": trace,
    }


def _recompute_snapshot(catalog: dict, snapshot: object) -> dict:
    if type(snapshot) is not dict or len(_canonical(snapshot)) > MAX_SNAPSHOT_BYTES:
        raise LineageError("Generation snapshot is invalid or exceeds its size limit.")
    parent_ids = snapshot.get("parent_ids")
    if type(parent_ids) is not list or len(parent_ids) != 2:
        raise LineageError("A generation snapshot must name exactly two parents.")
    expected = _generate_validated(catalog, parent_ids[0], parent_ids[1], snapshot.get("seed"))
    if _canonical(snapshot) != _canonical(expected):
        raise LineageError("Generation snapshot was altered or belongs to a different ruleset.")
    return expected


def load_catalog(data_dir: Path) -> dict:
    """Read and validate data_dir/lineages.json without writing or acquiring data."""
    path = Path(data_dir) / "lineages.json"
    with path.open("rb") as stream:
        contents = stream.read(MAX_CATALOG_BYTES + 1)
    if len(contents) > MAX_CATALOG_BYTES:
        raise LineageError("Catalog file exceeds one MiB.")

    def unique_object(pairs: list[tuple]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise LineageError("Duplicate JSON field in lineage catalog.")
            result[key] = value
        return result

    try:
        catalog = json.loads(contents.decode("utf-8"), object_pairs_hook=unique_object)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise LineageError("Catalog must contain valid UTF-8 JSON.") from exc
    return copy.deepcopy(_validate_catalog(catalog))


def generate_lineage(catalog: dict, parent_a: str, parent_b: str, seed: str) -> dict:
    """Generate deterministic potential/provenance; never grant executable skills."""
    valid = _validate_catalog(catalog)
    return _generate_validated(valid, parent_a, parent_b, seed)


def extend_catalog(catalog: dict, lineage: dict) -> dict:
    """Register only a recomputable output as a parent in a copied catalog.

    Registry order is topological. Original founders are supplied by the trusted
    catalog file; generated parents cannot assert their own traits or ancestry.
    """
    valid = _validate_catalog(catalog)
    expected = _recompute_snapshot(valid, lineage)
    result = copy.deepcopy(valid)
    existing = next((profile for profile in result["profiles"] if profile["id"] == expected["id"]), None)
    if existing is not None:
        if _canonical(existing) != _canonical(_profile_from_lineage(expected)):
            raise LineageError("A different profile already uses this lineage ID.")
        return result
    if (sum(profile["source_lineage"] is not None for profile in result["profiles"]) >= MAX_GENERATIONS
            or len(result["profiles"]) >= MAX_PROFILES):
        raise LineageError("The generated-parent registry is full; export and reset before continuing.")
    result["profiles"].append(_profile_from_lineage(expected))
    return result
