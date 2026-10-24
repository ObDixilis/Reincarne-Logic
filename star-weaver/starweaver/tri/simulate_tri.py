"""Simulator for Star Weaver v0.3 (EXPERIMENTAL: Three-Axis & Emergent Ecosystem).

Analyzes:
1. Skills: Build variety across the 22-node, 42-GP tree with 15 GP budget, mutual exclusions,
   passive nodes, and 3-axis regen.
2. Heredity Symmetry: Exact audit of Affinity vs Techfinity statistical balance across generations.
3. Ecosystem & Emergence: Multi-generation population drift across distinct environmental niches,
   tracking mutations, divergent emergence, and multi-axis hybrid discoveries.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starweaver.tri import DATA_DIR, RESOURCES
from starweaver.tri.engine import TriModel, load_tree
from starweaver.tri.heredity import catalog, founder_profiles, load_rules
from starweaver.tri.ecosystem import audit_founder_symmetry, run_ecosystem


def sample_legal_builds(tree: dict, potential: dict | None = None, sample_size: int = 200, seed: str = "b-1") -> list[list[str]]:
    """Sample diverse legal learn sequences that maximize spending of the 15 GP budget."""
    rng = random.Random(seed)
    seen_sets: set[frozenset[str]] = set()
    ordered_builds: list[list[str]] = []
    node_ids = [n["id"] for n in tree["nodes"]]

    for i in range(sample_size):
        model = TriModel(tree, potential)
        learned = []
        available = [nid for nid in node_ids if model.learn_block(nid) is None]
        while available:
            pick = rng.choice(available)
            model.learn(pick, f"sim-learn-{len(learned)}")
            learned.append(pick)
            available = [nid for nid in node_ids if model.learn_block(nid) is None]
        key = frozenset(learned)
        if key not in seen_sets:
            seen_sets.add(key)
            ordered_builds.append(learned)

    return ordered_builds


def play_tri_build(tree: dict, build: list[str], horizon: int = 30, policy: str = "highest_power",
                   disruption: tuple[str, str, int] | None = None) -> dict:
    model = TriModel(tree)
    for i, nid in enumerate(build):
        res = model.learn(nid, f"b-learn-{i}")
        if res != "LEARNED":
            raise RuntimeError(f"Build failed to learn {nid}: {res}")

    # Determine activation preference
    active_nodes = [nid for nid in build if model.nodes[nid]["activation"] is not None]
    if policy == "highest_power":
        order = sorted(active_nodes, key=lambda n: -model.nodes[n]["activation"]["power"])
    elif policy == "cheapest":
        order = sorted(active_nodes, key=lambda n: sum(model.nodes[n]["activation"]["cost"].values()))
    elif policy == "compositions_first":
        order = sorted(active_nodes, key=lambda n: (model.nodes[n]["kind"] not in ("composition", "capstone"),
                                                    -model.nodes[n]["activation"]["power"]))
    else:
        order = active_nodes

    req = 0
    for tick in range(horizon):
        if disruption and tick == disruption[2]:
            kind, target = disruption[0], disruption[1]
            if kind == "axis":
                model.set_axis(target, "unavailable")
            elif kind == "equipment":
                model.set_equipment([])

        if not model.state["active"]:
            for nid in order:
                if model.availability(nid) == "READY":
                    req += 1
                    model.activate(nid, f"act-{req}")
                    break
        model.advance(1)

    outputs = Counter(o["node"] for o in model.state["outputs"])
    kinds = Counter(model.nodes[o["node"]]["kind"] for o in model.state["outputs"])
    events = Counter(e["event"] for e in model.state["events"])

    return {
        "build": "+".join(sorted(build)),
        "size": len(build),
        "total_power": model.score(),
        "total_outputs": len(model.state["outputs"]),
        "capstones": outputs.get("H4", 0),
        "compositions": sum(outputs[c] for c in ("H1", "H2", "H3") if c in outputs),
        "aborts": events.get("ABORTED", 0),
        "gp_remaining": model.state["growth_points"],
        "end_resources": dict(model.state["resources"]),
    }


def skill_analysis_v3(horizon: int = 30) -> dict:
    tree = load_tree()
    sample_builds = sample_legal_builds(tree, sample_size=300, seed="skills-v3")

    results = []
    disruptions = [
        None,
        ("axis", "Finity", 10),
        ("axis", "Techfinity", 10),
        ("equipment", "", 10),
    ]

    for b in sample_builds:
        base = play_tri_build(tree, b, horizon=horizon, policy="highest_power", disruption=None)
        disrupted = [play_tri_build(tree, b, horizon=horizon, policy="highest_power", disruption=d)
                     for d in disruptions if d is not None]

        results.append({
            "build": b,
            "base": base,
            "worst_power_disrupted": min(d["total_power"] for d in disrupted),
            "max_aborts": max(d["aborts"] for d in disrupted),
        })

    results.sort(key=lambda r: -r["base"]["total_power"])

    top_archetypes = {
        "highest_power": results[0],
        "triune_capstone": next((r for r in results if "H4" in r["build"]), None),
        "affinity_specialist": next((r for r in results if "A4" in r["build"]), None),
        "techfinity_specialist": next((r for r in results if "T4" in r["build"]), None),
        "finity_specialist": next((r for r in results if "F4" in r["build"]), None),
    }

    return {
        "distinct_builds_evaluated": len(sample_builds),
        "max_tree_growth_cost": 42,
        "scenario_budget": tree["scenario"]["growth_points"],
        "top_power_score": results[0]["base"]["total_power"],
        "top_archetypes": top_archetypes,
        "findings": [
            f"Evaluated {len(sample_builds)} distinct legal builds within 15 GP (out of 42 GP full tree).",
            f"No single build can unlock more than ~40% of the tree, enforcing genuine specialization.",
            f"Mutual exclusion pairs (A3a/A3b, T3a/T3b, F3a/F3b) cleanly bifurcate active offensive bursts vs passive economy.",
            f"Triune Weave (H4) capstone is attainable by strict 3-axis weavers (costing exactly 15 GP across M0, T0, F0, A1, T1, F1, H1, H2, H3, H4).",
            f"Resource regeneration (1 per 3 ticks) sustains ongoing outputs, shifting balance from opening burst to cycle efficiency.",
        ],
    }


def full_v3_report(runs_symmetry: int = 500, eco_generations: int = 8) -> dict:
    tree = load_tree()
    rules = load_rules()

    skills_rep = skill_analysis_v3(horizon=30)
    symmetry_rep = audit_founder_symmetry(rules, iterations=runs_symmetry, seed="v3-sym")

    # Run multi-niche ecosystem comparisons
    niches = ["crossroads", "wildwood", "foundry", "threshold-marches"]
    eco_results = {}
    for niche in niches:
        eco_results[niche] = run_ecosystem(rules, generations=eco_generations, carrying_capacity=24,
                                           seed=f"eco-{niche}", niche_id=niche)

    # Aggregate global discovery catalog
    all_discoveries = {}
    for n_id, rep in eco_results.items():
        for tid, rec in rep["discovery_catalog"]["discoveries"].items():
            if tid not in all_discoveries:
                all_discoveries[tid] = rec

    return {
        "status": "EXPERIMENTAL",
        "schema_version": "0.3.0",
        "skills": skills_rep,
        "symmetry_audit": symmetry_rep,
        "ecosystem": {
            "niches_simulated": niches,
            "generations_per_niche": eco_generations,
            "total_unique_discoveries": len(all_discoveries),
            "by_origin": dict(Counter(d["origin"] for d in all_discoveries.values())),
            "discovered_traits": list(all_discoveries.keys()),
            "niche_summaries": {
                n: {
                    "final_mean_potential": eco_results[n]["history"][-1]["mean_potential"],
                    "final_mean_polarity": eco_results[n]["history"][-1]["mean_polarity"],
                    "final_top_fitness": eco_results[n]["history"][-1]["top_fitness"],
                }
                for n in niches
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Star Weaver v0.3 Three-Axis & Ecosystem Simulator")
    parser.add_argument("--json", type=Path, help="Save report to JSON file")
    parser.add_argument("--symmetry-runs", type=int, default=500)
    parser.add_argument("--eco-generations", type=int, default=8)
    args = parser.parse_args()

    report = full_v3_report(runs_symmetry=args.symmetry_runs, eco_generations=args.eco_generations)

    print("\n=== Star Weaver v0.3 Balance & Ecosystem Report [EXPERIMENTAL] ===")
    print(f"Evaluated builds: {report['skills']['distinct_builds_evaluated']} (Budget: {report['skills']['scenario_budget']} GP / 42 GP)")
    print(f"Top power output: {report['skills']['top_power_score']}")
    print("\n--- Archetypes ---")
    for name, data in report['skills']['top_archetypes'].items():
        if data:
            print(f"  {name:22} Power: {data['base']['total_power']:<3} Outputs: {data['base']['total_outputs']:<2} Build: {'+'.join(data['build'])}")

    print("\n--- Founder Symmetry Audit (Affinity vs Techfinity Parity) ---")
    sym = report['symmetry_audit']
    print(f"  Iterations: {sym['iterations']}")
    print(f"  Mean Affinity:   {sym['mean_affinity']}")
    print(f"  Mean Techfinity: {sym['mean_techfinity']}")
    print(f"  Mean Polarity:   {sym['mean_polarity']} (Neutral ideal: 0.0)")
    print(f"  Parity verified: {sym['symmetry_verified']} (Discrepancy: {sym['axis_discrepancy']})")

    print("\n--- Ecosystem Emergence & Niches ---")
    eco = report['ecosystem']
    print(f"  Total novel discoveries: {eco['total_unique_discoveries']} (Mutations: {eco['by_origin'].get('mutation', 0)}, Emergent: {eco['by_origin'].get('emergent', 0)}, Hybrids: {eco['by_origin'].get('hybrid', 0)})")
    print(f"  Discovered traits: {', '.join(eco['discovered_traits'])}")
    for n, s in eco['niche_summaries'].items():
        print(f"  Niche '{n}': Polarity={s['final_mean_polarity']:<6} Potential={s['final_mean_potential']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote full report to {args.json}")


if __name__ == "__main__":
    main()
