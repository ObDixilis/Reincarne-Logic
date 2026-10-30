"""Three-axis heredity with polarity, mutation, divergent emergence and hybrids (EXPERIMENTAL).

Profiles are plain dicts:
    {id, label, generation, parents, route, seed, potential{Affinity,Techfinity,Finity},
     polarity, traits:[{id, origin, dormant, from}], founders, status,
     learned_skills: [], active_axis_access: {...: "unavailable"}}

Every child is a pure function of (parent_a, parent_b, route, seed, rules), so
results are reproducible and auditable. Potential never grants skills or access.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path

from . import AXES, DATA_DIR

ORIGINS = ("founder", "inherited", "mutation", "emergent", "hybrid")
_AT = {"Affinity": "Techfinity", "Techfinity": "Affinity", "Finity": "Finity"}


def load_rules(path: Path | None = None) -> dict:
    rules = json.loads(Path(path or DATA_DIR / "heredity.json").read_text(encoding="utf-8"))
    validate_rules(rules)
    return rules


def catalog(rules: dict) -> dict:
    """Every trait the system can produce, keyed by id, with its origin class."""
    out = {}
    for t in rules["traits"]:
        out[t["id"]] = {**t, "class": "founder"}
    for t in rules["mutations"]:
        out[t["id"]] = {**t, "class": "mutation"}
    for t in rules["emergence"]:
        out[t["id"]] = {**t, "class": "emergent"}
    for t in rules["hybrids"]:
        out[t["id"]] = {**t, "class": "hybrid"}
    return out


def _mirror_axis(axis):
    return None if axis is None else _AT[axis]


def _mirror_tags(tags, rules):
    tm = rules["tag_mirror"]
    return sorted(tm.get(t, t) for t in tags)


def _mirror_pot(d):
    return {_AT[k]: v for k, v in d.items()}


def validate_rules(rules: dict) -> None:
    if rules.get("schema_version") != "0.3.0" or rules.get("status") != "EXPERIMENTAL":
        raise ValueError("Heredity rules must be schema 0.3.0 and EXPERIMENTAL")
    cat = {}
    for group in ("traits", "mutations", "emergence", "hybrids"):
        for t in rules[group]:
            if t["id"] in cat:
                raise ValueError(f"Duplicate trait id {t['id']}")
            if t["axis"] not in (None, *AXES):
                raise ValueError(f"{t['id']}: bad axis")
            cat[t["id"]] = (group, t)
    routes = set(rules["routes"])
    if set(rules["route_mirror"]) != routes:
        raise ValueError("route_mirror must cover every route")
    for r in rules["routes"].values():
        if set(r["potential_weight"]) != set(AXES):
            raise ValueError("Route weights must cover all axes")
    # Mirror symmetry: the Affinity/Techfinity sides must be exact reflections.
    for tid, (group, t) in cat.items():
        m = cat.get(t["mirror"])
        if m is None or m[0] != group or m[1]["mirror"] != tid:
            raise ValueError(f"{tid}: mirror must exist in the same group and point back")
        mt = m[1]
        if mt["axis"] != _mirror_axis(t["axis"]) or sorted(mt["tags"]) != _mirror_tags(t["tags"], rules):
            raise ValueError(f"{tid}: mirror axis/tags are not a reflection")
        if group == "traits" and sorted(mt["carried_by"]) != sorted(rules["route_mirror"][x] for x in t["carried_by"]):
            raise ValueError(f"{tid}: mirror carried_by is not a reflection")
        if group == "mutations" and mt["weight"] != t["weight"]:
            raise ValueError(f"{tid}: mirror weight differs")
        if group == "emergence":
            want = {rules["tag_mirror"].get(k, k): v for k, v in t["requires_tags"].items()}
            if mt["requires_tags"] != want or mt["requires_potential"] != _mirror_pot(t["requires_potential"]) \
                    or mt["chance"] != t["chance"]:
                raise ValueError(f"{tid}: mirror emergence rule is not a reflection")
        if group == "hybrids" and (mt["min"] != _mirror_pot(t["min"]) or mt["max"] != _mirror_pot(t["max"])):
            raise ValueError(f"{tid}: mirror hybrid thresholds are not a reflection")
    for t in rules["traits"]:
        if not set(t["carried_by"]) <= routes:
            raise ValueError(f"{t['id']}: unknown route")
    founders = {f["id"]: f for f in rules["founders"]}
    for fid, f in founders.items():
        if set(f["potential"]) != set(AXES) or not -1 <= f["polarity"] <= 1:
            raise ValueError(f"{fid}: invalid potential/polarity")
        for t in f["traits"]:
            if t not in cat or cat[t][0] != "traits":
                raise ValueError(f"{fid}: unknown founder trait {t}")
        m = founders.get(f["mirror"])
        if (m is None or m["mirror"] != fid or m["potential"] != _mirror_pot(f["potential"])
                or abs(m["polarity"] + f["polarity"]) > 1e-9
                or sorted(m["traits"]) != sorted(cat[t][1]["mirror"] for t in f["traits"])):
            raise ValueError(f"{fid}: founder mirror is not an exact reflection")
    niches = {n["id"]: n for n in rules["niches"]}
    for nid, n in niches.items():
        m = niches.get(n["mirror"])
        if (m is None or m["weights"] != _mirror_pot(n["weights"]) or abs(m["polarity_pref"] + n["polarity_pref"]) > 1e-9
                or m["tag_bonus"] != {rules["tag_mirror"].get(k, k): v for k, v in n["tag_bonus"].items()}):
            raise ValueError(f"{nid}: niche mirror is not a reflection")
    if "tradition_mirror" in rules and "traditions" in rules:
        for fid, trad in rules["traditions"].items():
            m_fid = founders[fid]["mirror"]
            m_trad = rules["traditions"][m_fid]
            if rules["tradition_mirror"].get(trad) != m_trad:
                raise ValueError(f"{fid}: tradition mirror reflection mismatch")


def founder_profiles(rules: dict) -> dict:
    out = {}
    traditions = rules.get("traditions", {})
    for f in rules["founders"]:
        out[f["id"]] = {
            "id": f["id"], "label": f["label"], "generation": 0, "parents": [], "route": None, "seed": None,
            "potential": {a: float(f["potential"][a]) for a in AXES}, "polarity": float(f["polarity"]),
            "traits": [{"id": t, "origin": "founder", "dormant": False, "from": []} for t in sorted(f["traits"])],
            "founders": [f["id"]], "status": "EXPERIMENTAL", "learned_skills": [],
            "mentorship_tradition": traditions.get(f["id"], "Crossroads Open Guild"),
            "active_axis_access": {a: "unavailable" for a in AXES},
        }
    return out


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def expressed_tags(profile: dict, cat: dict) -> dict:
    counts: dict[str, int] = {}
    for t in profile["traits"]:
        if not t["dormant"]:
            for tag in cat[t["id"]]["tags"]:
                counts[tag] = counts.get(tag, 0) + 1
    return counts


def make_child(rules: dict, a: dict, b: dict, seed: str, route: str = "biological",
               mutation_rate: float | None = None, cat: dict | None = None) -> dict:
    if route not in rules["routes"]:
        raise ValueError(f"Unknown route {route}")
    if a["id"] == b["id"]:
        raise ValueError("A cross needs two distinct parents")
    cat = cat or catalog(rules)
    blend, r = rules["blend"], rules["routes"][route]
    key = hashlib.sha256(f"{a['id']}|{b['id']}|{route}|{seed}|{rules['ruleset_id']}".encode()).hexdigest()
    rng = random.Random(key)
    cid = "L-" + key[:14]

    # Polarity: parental mean + noise + feedback from the parents' Affinity/Techfinity balance.
    mean_pot = {ax: (a["potential"][ax] + b["potential"][ax]) / 2 for ax in AXES}
    pol = (a["polarity"] + b["polarity"]) / 2 + rng.gauss(0, blend["polarity_sigma"])
    pol += blend["polarity_feedback"] * (mean_pot["Techfinity"] - mean_pot["Affinity"]) / 100
    pol = _clamp(pol, -1.0, 1.0)

    pot = {}
    for ax in AXES:
        w = r["potential_weight"][ax]
        pot[ax] = mean_pot[ax] * w + blend["regression_mean"] * (1 - w) + rng.gauss(0, blend["potential_sigma"])
    lean = pol * blend["polarity_pull"]
    pot["Affinity"] -= lean
    pot["Techfinity"] += lean
    conv = blend["convergence"]
    if pot["Affinity"] >= conv["threshold"] and pot["Techfinity"] >= conv["threshold"] and abs(pol) <= conv["window"]:
        pot["Finity"] += conv["bonus"] * (1 - abs(pol) / conv["window"])
    pot = {ax: round(_clamp(v, 0.0, 100.0), 1) for ax, v in pot.items()}

    def dormant(tid):
        axis = cat[tid]["axis"]
        return axis is not None and pot[axis] < blend["dormant_below"]

    traits: dict[str, dict] = {}
    held_a = {t["id"] for t in a["traits"]}
    held_b = {t["id"] for t in b["traits"]}
    for tid in sorted(held_a | held_b):
        info = cat[tid]
        carried = info.get("carried_by")
        if info["class"] == "founder" and carried is not None and route not in carried:
            continue
        both = tid in held_a and tid in held_b
        rate = r["trait_rate"]["both" if both else "one"]
        if rng.random() < rate:
            traits[tid] = {"id": tid, "origin": "inherited", "dormant": dormant(tid),
                           "from": sorted(p["id"] for p, h in ((a, held_a), (b, held_b)) if tid in h)}

    # Mutation: rare traits neither parent carried, biased toward the child's strong axes.
    m_rate = rules["mutation"]["rate"] if mutation_rate is None else mutation_rate
    pool = rules["mutations"]
    for _ in range(rules["mutation"]["slots"]):
        if rng.random() < m_rate:
            weights = [m["weight"] * (1 + (pot[m["axis"]] / 100 if m["axis"] else 0.5)) for m in pool]
            pick = rng.choices(pool, weights=weights)[0]
            if pick["id"] not in traits:
                traits[pick["id"]] = {"id": pick["id"], "origin": "mutation", "dormant": dormant(pick["id"]), "from": []}

    # Divergent emergence: combined parental tags + child potential unlock new traits.
    tags: dict[str, int] = {}
    for p in (a, b):
        for k, v in expressed_tags(p, cat).items():
            tags[k] = tags.get(k, 0) + v
    for k in {t["id"] for t in traits.values() if t["origin"] == "mutation"}:
        for tag in cat[k]["tags"]:
            tags[tag] = tags.get(tag, 0) + 1
    for rule in rules["emergence"]:
        if rule["id"] in traits:
            continue
        if all(tags.get(k, 0) >= v for k, v in rule["requires_tags"].items()) and \
                all(pot[ax] >= v for ax, v in rule["requires_potential"].items()):
            if rng.random() < rule["chance"]:
                traits[rule["id"]] = {"id": rule["id"], "origin": "emergent", "dormant": False,
                                      "from": [a["id"], b["id"]]}

    # Hybrids: deterministic from the child's own multi-axis potential profile.
    for rule in rules["hybrids"]:
        if all(pot[ax] >= v for ax, v in rule["min"].items()) and all(pot[ax] <= v for ax, v in rule["max"].items()):
            traits[rule["id"]] = {"id": rule["id"], "origin": "hybrid", "dormant": False, "from": []}

    # Cultural & flow arts mentorship transmission (separate from biological potential)
    trad_a = a.get("mentorship_tradition", "Crossroads Open Guild")
    trad_b = b.get("mentorship_tradition", "Crossroads Open Guild")
    if route == "mentorship":
        child_tradition = trad_a  # Direct taught lineage from primary mentor
    elif route == "blueprint":
        child_tradition = "Foundry Artisan Guild"
    elif route == "resonant":
        child_tradition = "Starlit Weavers Circle" if pol < 0 else "Lattice Engineers Guild"
    else:  # biological: family craft or balanced synthesis
        child_tradition = trad_a if rng.random() < 0.5 else trad_b

    return {
        "id": cid, "label": cid, "generation": max(a["generation"], b["generation"]) + 1,
        "parents": [a["id"], b["id"]], "route": route, "seed": seed,
        "potential": pot, "polarity": round(pol, 3),
        "traits": [traits[k] for k in sorted(traits)],
        "founders": sorted(set(a["founders"]) | set(b["founders"])),
        "status": "EXPERIMENTAL", "learned_skills": [],
        "mentorship_tradition": child_tradition,
        "active_axis_access": {ax: "unavailable" for ax in AXES},
    }


def mirror_profile(rules: dict, p: dict) -> dict:
    cat = catalog(rules)
    q = copy.deepcopy(p)
    q["potential"] = _mirror_pot(p["potential"])
    q["polarity"] = -p["polarity"]
    for t in q["traits"]:
        t["id"] = cat[t["id"]]["mirror"]
    q["traits"].sort(key=lambda t: t["id"])
    if "mentorship_tradition" in q and "tradition_mirror" in rules:
        q["mentorship_tradition"] = rules["tradition_mirror"].get(q["mentorship_tradition"], q["mentorship_tradition"])
    return q


def skill_candidates(profile: dict, tree: dict, threshold: float = 40) -> list[str]:
    """Nodes whose axes all have potential >= threshold. Suggestion only; grants nothing."""
    pot = profile["potential"]
    return [n["id"] for n in tree["nodes"] if all(pot[a] >= threshold for a in n["axes"])]
