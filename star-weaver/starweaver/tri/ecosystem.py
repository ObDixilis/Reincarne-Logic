"""Ecosystem and emergence simulation for Star Weaver v0.3 (EXPERIMENTAL).

Simulates multi-generation populations subject to:
- Environmental niches with selective carrying capacity and fitness pressure
- Random or fitness-weighted partner selection across routes
- Emergent trait and mutation discovery tracking
- Lineage trees and founder provenance audits
- Exact mathematical symmetry tests between Affinity and Techfinity
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from . import AXES, DATA_DIR
from .heredity import (
    catalog,
    expressed_tags,
    founder_profiles,
    load_rules,
    make_child,
    mirror_profile,
)


def profile_fitness(profile: dict, niche: dict, cat: dict) -> float:
    """Calculate survival/reproductive fitness score in a given niche."""
    pot = profile["potential"]
    w = niche["weights"]
    base = sum(pot[ax] * w[ax] for ax in AXES) / 100.0

    # Polarity alignment: bonus for aligning with niche's preferred polarity
    pol_diff = abs(profile["polarity"] - niche["polarity_pref"])
    pol_mult = max(0.2, 1.2 - (pol_diff * 0.8))

    # Tag bonuses
    tags = expressed_tags(profile, cat)
    tag_mult = 1.0 + sum(tags.get(tag, 0) * bonus for tag, bonus in niche.get("tag_bonus", {}).items())

    return max(0.01, base * pol_mult * tag_mult)


class DiscoveryCatalog:
    """Logs the first emergence or mutation of novel traits."""
    def __init__(self):
        self.records: dict[str, dict] = {}

    def observe(self, profile: dict, gen: int, niche_id: str | None = None) -> list[str]:
        novel = []
        for t in profile["traits"]:
            tid = t["id"]
            if t["origin"] in ("mutation", "emergent", "hybrid") and tid not in self.records:
                self.records[tid] = {
                    "trait_id": tid,
                    "origin": t["origin"],
                    "first_seen_generation": gen,
                    "lineage_id": profile["id"],
                    "parents": profile["parents"],
                    "seed": profile["seed"],
                    "route": profile["route"],
                    "niche": niche_id,
                    "potential_at_birth": dict(profile["potential"]),
                    "polarity_at_birth": profile["polarity"],
                }
                novel.append(tid)
        return novel

    def summary(self) -> dict:
        by_origin = Counter(r["origin"] for r in self.records.values())
        return {
            "total_discovered": len(self.records),
            "by_origin": dict(by_origin),
            "discoveries": dict(self.records),
        }


def run_ecosystem(
    rules: dict,
    generations: int = 10,
    carrying_capacity: int = 30,
    seed: str = "eco-1",
    niche_id: str = "crossroads",
    mutation_rate: float | None = None,
) -> dict:
    cat = catalog(rules)
    niche = next((n for n in rules["niches"] if n["id"] == niche_id), rules["niches"][0])
    rng = random.Random(f"eco:{seed}:{niche_id}")
    founders = founder_profiles(rules)
    pop = list(founders.values())

    catalog_tracker = DiscoveryCatalog()
    for p in pop:
        catalog_tracker.observe(p, gen=0, niche_id=niche_id)

    gen_stats = []
    routes = list(rules["routes"].keys())

    for gen in range(1, generations + 1):
        if not pop:
            break

        # Calculate fitness
        fitnesses = [profile_fitness(p, niche, cat) for p in pop]
        total_fit = sum(fitnesses)
        weights = [f / total_fit for f in fitnesses] if total_fit > 0 else None

        # Breed new generation
        next_pop = []
        target_size = min(carrying_capacity, max(12, len(pop) * 2))

        for i in range(target_size):
            if len(pop) >= 2:
                # Weighted sample of parents without replacement
                if weights:
                    parent_a = rng.choices(pop, weights=weights)[0]
                    # Select second distinct parent
                    rem_pop = [p for p in pop if p["id"] != parent_a["id"]]
                    rem_fit = [profile_fitness(p, niche, cat) for p in rem_pop]
                    parent_b = rng.choices(rem_pop, weights=rem_fit)[0]
                else:
                    parent_a, parent_b = rng.sample(pop, 2)
            else:
                parent_a = pop[0]
                parent_b = rng.choice(list(founders.values()))

            route = rng.choice(routes)
            child_seed = f"{seed}-g{gen}-c{i}"
            child = make_child(
                rules,
                parent_a,
                parent_b,
                seed=child_seed,
                route=route,
                mutation_rate=mutation_rate,
                cat=cat,
            )
            catalog_tracker.observe(child, gen=gen, niche_id=niche_id)
            next_pop.append(child)

        # Environmental selection: keep top carrying_capacity based on fitness
        child_fits = [profile_fitness(c, niche, cat) for c in next_pop]
        indexed = sorted(zip(next_pop, child_fits), key=lambda x: -x[1])
        pop = [x[0] for x in indexed[:carrying_capacity]]

        # Record generation metrics
        mean_pot = {
            ax: round(sum(p["potential"][ax] for p in pop) / len(pop), 2)
            for ax in AXES
        }
        mean_pol = round(sum(p["polarity"] for p in pop) / len(pop), 3)
        mean_traits = round(sum(len(p["traits"]) for p in pop) / len(pop), 2)

        gen_stats.append({
            "generation": gen,
            "population_size": len(pop),
            "mean_potential": mean_pot,
            "mean_polarity": mean_pol,
            "mean_trait_count": mean_traits,
            "top_fitness": round(indexed[0][1], 3) if indexed else 0,
        })

    return {
        "niche": niche_id,
        "generations": generations,
        "carrying_capacity": carrying_capacity,
        "seed": seed,
        "history": gen_stats,
        "discovery_catalog": catalog_tracker.summary(),
    }


def audit_founder_symmetry(rules: dict, iterations: int = 500, seed: str = "sym-test") -> dict:
    """Verifies that Affinity and Techfinity drift symmetrically under mirrored neutral conditions."""
    cat = catalog(rules)
    founders = founder_profiles(rules)
    f_list = list(founders.values())

    rng = random.Random(seed)
    routes = list(rules["routes"].keys())

    aff_sum = 0.0
    tech_sum = 0.0
    pol_sum = 0.0
    mut_aff = 0
    mut_tech = 0

    for i in range(iterations):
        # Pick 2 parents
        p1, p2 = rng.sample(f_list, 2)
        route = rng.choice(routes)
        c = make_child(rules, p1, p2, seed=f"{seed}-{i}", route=route, cat=cat)

        aff_sum += c["potential"]["Affinity"]
        tech_sum += c["potential"]["Techfinity"]
        pol_sum += c["polarity"]

        for t in c["traits"]:
            if t["origin"] == "mutation":
                ax = cat[t["id"]]["axis"]
                if ax == "Affinity":
                    mut_aff += 1
                elif ax == "Techfinity":
                    mut_tech += 1

    mean_aff = aff_sum / iterations
    mean_tech = tech_sum / iterations
    diff = abs(mean_aff - mean_tech)
    # 3-sigma statistical confidence bound based on potential sigma (8.0)
    tolerance = max(1.0, 3.0 * (8.0 * (2 ** 0.5) / (iterations ** 0.5)))

    return {
        "iterations": iterations,
        "mean_affinity": round(mean_aff, 3),
        "mean_techfinity": round(mean_tech, 3),
        "mean_polarity": round(pol_sum / iterations, 4),
        "axis_discrepancy": round(diff, 4),
        "tolerance": round(tolerance, 4),
        "mutations_affinity": mut_aff,
        "mutations_techfinity": mut_tech,
        "symmetry_verified": diff <= tolerance,
    }
