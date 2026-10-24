"""Headless balance simulator for Star Weaver (read-only; never edits data or saves).

Usage:
    python simulate.py                      # both reports, default settings
    python simulate.py skills --horizon 24
    python simulate.py lineage --runs 500 --generations 8 --seed bal-1
    python simulate.py --json report.json   # also write machine-readable output

Skill report: exhaustively enumerates every legal learn order within the growth
budget, then plays each build with several activation policies and an optional
mid-run axis/equipment loss, reporting outputs, resource exhaustion and aborts.

Lineage report: runs seeded random multi-generation breeding populations using
the real heredity engine (extend_catalog keeps it recomputable) and reports axis
potential prevalence, trait frequencies, channel survival and branch statuses.
All results are EXPERIMENTAL advisory data; nothing here changes canon.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from starweaver.engine import Model, RESOURCES  # noqa: E402
from starweaver import heredity  # noqa: E402

DATA = ROOT / "data"


# ---------------------------------------------------------------- skills
def load_fixture() -> dict:
    return json.loads((DATA / "star-weaver.fixture.json").read_text(encoding="utf-8"))


def legal_builds(fixture: dict) -> list[tuple[str, ...]]:
    """Every distinct learn sequence that succeeds until no further learn is possible."""
    builds: set[tuple[str, ...]] = set()

    def explore(model: Model, seq: tuple[str, ...]):
        progressed = False
        for node in model.nodes:
            trial = Model.restore(fixture, model.save()) if hasattr(Model, "restore") else None
            if trial is None:
                raise RuntimeError("Model.restore unavailable")
            if trial.learn(node, f"sim-{len(seq)}-{node}") == "LEARNED":
                progressed = True
                explore(trial, seq + (node,))
        if not progressed:
            builds.add(seq)

    explore(Model(fixture), ())
    return sorted(builds)


POLICIES = {
    "expressions_first": lambda nodes: [n for n in ("A1", "T1", "H1", "M0", "T0") if n in nodes],
    "composed_first": lambda nodes: (["H1"] if "H1" in nodes else []) + [n for n in nodes if n != "H1"],
    "cheapest_first": lambda nodes: [n for n in ("M0", "T0", "A1", "T1", "H1") if n in nodes],
}

DISRUPTIONS = {
    "none": None,
    "lose_techfinity@3": ("axis", "Techfinity", 3),
    "lose_affinity@3": ("axis", "Affinity", 3),
    "lose_lamp@3": ("equipment", None, 3),
}


def play(fixture: dict, build: tuple[str, ...], policy: str, disruption: str, horizon: int) -> dict:
    model = Model(fixture)
    for i, node in enumerate(build):
        assert model.learn(node, f"learn-{i}") == "LEARNED"
    order = POLICIES[policy](list(dict.fromkeys(build)))
    plan = DISRUPTIONS[disruption]
    req = 0
    for tick in range(horizon):
        if plan and tick == plan[2]:
            if plan[0] == "axis":
                model.set_axis(plan[1], "unavailable")
            else:
                model.set_equipment([])
        if not model.state["active"]:
            for node in order:
                if model.availability(node) == "READY":
                    req += 1
                    model.activate(node, f"act-{req}")
                    break
        model.advance(1)
    outputs = Counter(o["node"] for o in model.state["outputs"])
    events = Counter(e["event"] for e in model.state["events"])
    return {
        "build": "+".join(build), "policy": policy, "disruption": disruption,
        "outputs": dict(outputs), "total_outputs": sum(outputs.values()),
        "beacons": outputs.get("H1", 0), "aborts": events.get("ABORTED", 0),
        "leftover_growth": model.state["growth_points"],
        "leftover_resources": dict(model.state["resources"]),
        "exhausted": all(model.state["resources"][r] == 0 for r in RESOURCES),
    }


def skill_report(horizon: int) -> dict:
    fixture = load_fixture()
    builds = legal_builds(fixture)
    rows = [play(fixture, b, p, d, horizon)
            for b in builds for p in POLICIES for d in DISRUPTIONS]
    by_build = defaultdict(list)
    for r in rows:
        by_build[r["build"]].append(r)
    summary = []
    for build, rs in by_build.items():
        base = [r for r in rs if r["disruption"] == "none"]
        summary.append({
            "build": build,
            "best_outputs": max(r["total_outputs"] for r in base),
            "best_beacons": max(r["beacons"] for r in base),
            "worst_disrupted_outputs": min(r["total_outputs"] for r in rs),
            "leftover_growth": rs[0]["leftover_growth"],
        })
    summary.sort(key=lambda s: (-s["best_beacons"], -s["best_outputs"], s["build"]))
    unique_sets = Counter(frozenset(s["build"].split("+")) for s in summary)
    findings = []
    full = [s for s in summary if s["best_beacons"] > 0]
    findings.append(f"{len(builds)} legal learn orders collapse to {len(unique_sets)} distinct skill sets.")
    findings.append(f"{len(full)} of {len(builds)} orders reach Woven Beacon"
                    + ("." if len(full) == len(builds) else "; the rest end with H1 locked."))
    if summary:
        top = max(summary, key=lambda s: s["best_outputs"])
        findings.append(f"Most total outputs: {top['build']} ({top['best_outputs']}) - "
                        f"starting resources (focus/charge) cap output, not cooldowns.")
    beacon_max = max((s["best_beacons"] for s in summary), default=0)
    findings.append(f"Max beacons per scenario: {beacon_max} (each costs 1 focus + 1 charge from a pool of 3/3).")
    return {"horizon": horizon, "legal_builds": len(builds), "build_summary": summary,
            "findings": findings, "runs": rows}


# ---------------------------------------------------------------- lineage
def lineage_report(runs: int, generations: int, population: int, seed: str) -> dict:
    base = heredity.load_catalog(DATA)
    founders = [p["id"] for p in base["profiles"]]
    potential_by_gen = defaultdict(Counter)
    trait_by_gen = defaultdict(Counter)
    channel_by_gen = defaultdict(Counter)
    branch_status = Counter()
    branch_by_kind = defaultdict(Counter)
    extinct_axis = Counter()
    sizes = defaultdict(list)
    errors = Counter()
    for run in range(runs):
        rng = random.Random(hashlib.sha256(f"{seed}:{run}".encode()).hexdigest())
        catalog = base
        pool = list(founders)
        made = 0
        for gen in range(1, generations + 1):
            children = []
            for i in range(population):
                a, b = rng.sample(pool, 2)
                try:
                    child = heredity.generate_lineage(catalog, a, b, f"{seed}-{run}-{gen}-{i}")
                except heredity.LineageError as exc:
                    errors[str(exc)[:80]] += 1
                    continue
                children.append(child)
            if not children:
                break
            alive = {"Affinity": False, "Techfinity": False}
            for child in children:
                pot = child["axis_potential"]
                key = "+".join(ax for ax in ("Affinity", "Techfinity") if pot[ax]) or "none"
                potential_by_gen[gen][key] += 1
                for ax in alive:
                    alive[ax] |= pot[ax]
                sizes[gen].append(len(child["traits"]))
                for t in child["traits"]:
                    trait_by_gen[gen][t["id"]] += 1
                    channel_by_gen[gen][t["channel"]] += 1
                for br in child["branches"]:
                    status = br.get("status", "?")
                    branch_status[status] += 1
                    branch_by_kind[br.get("id", br.get("kind", "?"))][status] += 1
            for ax, ok in alive.items():
                if not ok:
                    extinct_axis[(gen, ax)] += 1
            # next generation breeds from survivors (registered so they stay recomputable)
            next_pool = []
            for child in children:
                if made >= heredity.MAX_GENERATIONS - 1:
                    break
                try:
                    catalog = heredity.extend_catalog(catalog, child)
                    next_pool.append(child["id"])
                    made += 1
                except heredity.LineageError as exc:
                    errors[str(exc)[:80]] += 1
            if len(next_pool) < 2:
                next_pool += rng.sample(founders, 2)  # immigration keeps the run alive
            pool = next_pool
    total = lambda c: sum(c.values()) or 1  # noqa: E731
    per_gen = []
    for gen in sorted(potential_by_gen):
        pc = potential_by_gen[gen]
        per_gen.append({
            "generation": gen, "offspring": total(pc),
            "potential_share": {k: round(v / total(pc), 3) for k, v in sorted(pc.items())},
            "mean_traits": round(sum(sizes[gen]) / max(len(sizes[gen]), 1), 2),
            "channel_share": {k: round(v / total(channel_by_gen[gen]), 3)
                              for k, v in sorted(channel_by_gen[gen].items())},
            "top_traits": trait_by_gen[gen].most_common(6),
        })
    findings = []
    if per_gen:
        first, last = per_gen[0], per_gen[-1]
        d1 = first["potential_share"].get("Affinity+Techfinity", 0)
        dn = last["potential_share"].get("Affinity+Techfinity", 0)
        findings.append(f"Dual-axis potential: {d1:.1%} in gen 1 -> {dn:.1%} in gen {last['generation']}.")
        n1, nn = first["potential_share"].get("none", 0), last["potential_share"].get("none", 0)
        findings.append(f"No-axis offspring: {n1:.1%} -> {nn:.1%}.")
        findings.append(f"Mean inherited traits: {first['mean_traits']} -> {last['mean_traits']}.")
    if extinct_axis:
        findings.append("Axis potential went extinct within a generation in some runs: "
                        + ", ".join(f"{ax}@g{g}x{n}" for (g, ax), n in sorted(extinct_axis.items())[:6]))
    findings.append("Reminder: potential never grants ranks, equipment or active axis access.")
    return {"runs": runs, "generations": generations, "population": population, "seed": seed,
            "per_generation": per_gen, "branch_status": dict(branch_status),
            "branch_by_kind": {k: dict(v) for k, v in branch_by_kind.items()},
            "errors": dict(errors), "findings": findings, "status": "EXPERIMENTAL"}


# ---------------------------------------------------------------- cli
def print_skills(rep: dict) -> None:
    print(f"\n== Skill balance (horizon {rep['horizon']} ticks) ==")
    print(f"{'build':32} {'best out':>8} {'beacons':>7} {'worst disrupted':>15} {'gp left':>7}")
    for s in rep["build_summary"]:
        print(f"{s['build']:32} {s['best_outputs']:>8} {s['best_beacons']:>7} "
              f"{s['worst_disrupted_outputs']:>15} {s['leftover_growth']:>7}")
    for f in rep["findings"]:
        print(" -", f)


def print_lineage(rep: dict) -> None:
    print(f"\n== Lineage drift ({rep['runs']} runs x {rep['generations']} gens x "
          f"{rep['population']} offspring, seed {rep['seed']}) [EXPERIMENTAL] ==")
    for g in rep["per_generation"]:
        print(f" g{g['generation']:<2} n={g['offspring']:<5} traits~{g['mean_traits']:<5} "
              f"potential={g['potential_share']}")
    print(" branch statuses:", rep["branch_status"])
    if rep["errors"]:
        print(" engine refusals:", rep["errors"])
    for f in rep["findings"]:
        print(" -", f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=("all", "skills", "lineage", "v3"), default="all")
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--generations", type=int, default=6)
    ap.add_argument("--population", type=int, default=4)
    ap.add_argument("--seed", default="balance-1")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    if args.mode == "v3":
        from starweaver.tri.simulate_tri import full_v3_report
        sym_runs = 500 if args.runs == 200 else args.runs
        report = full_v3_report(runs_symmetry=sym_runs, eco_generations=args.generations)
        print("\n=== Star Weaver v0.3 Balance & Ecosystem Report [EXPERIMENTAL] ===")
        print(f"Evaluated builds: {report['skills']['distinct_builds_evaluated']} (Budget: {report['skills']['scenario_budget']} GP / 42 GP)")
        print(f"Top power output: {report['skills']['top_power_score']}")
        print("\n--- Archetypes ---")
        for name, data in report['skills']['top_archetypes'].items():
            if data:
                print(f"  {name:22} Power: {data['base']['total_power']:<3} Outputs: {data['base']['total_outputs']:<2} Build: {'+'.join(data['build'])}")
        sym = report['symmetry_audit']
        print("\n--- Founder Symmetry Audit ---")
        print(f"  Mean Affinity: {sym['mean_affinity']} | Mean Techfinity: {sym['mean_techfinity']} | Parity verified: {sym['symmetry_verified']}")
        eco = report['ecosystem']
        print(f"\n--- Ecosystem Emergence ({eco['total_unique_discoveries']} discoveries) ---")
        print(f"  Discovered: {', '.join(eco['discovered_traits'])}")
        if args.json:
            args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"\nWrote {args.json}")
        return 0

    out = {}
    if args.mode in ("all", "skills"):
        out["skills"] = skill_report(args.horizon)
        print_skills(out["skills"])
    if args.mode in ("all", "lineage"):
        out["lineage"] = lineage_report(args.runs, args.generations, args.population, args.seed)
        print_lineage(out["lineage"])
    if args.json:
        args.json.write_text(json.dumps(out, indent=2, default=list), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
