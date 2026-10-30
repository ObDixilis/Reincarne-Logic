# Experimental hereditary and succession pathways

This module implements `SW-HEREDITY-EXPERIMENT-001` for the Star Weaver workbench. The approved skill design is SW-SKILL-001. The hereditary policies, synthetic profiles, transmission thresholds, and branch suggestions are explicit experiments added for the requested implementation. They do not establish canonical species, bloodlines, genetic laws, or the source of axis access.

Affinity and Techfinity remain independent. Finity has no trait, rank, inheritance role, resource, prerequisite, parent system, or gameplay gate here. The catalog accepts only Affinity, Techfinity, or no axis for a trait. Ordinary methods remain eligible independently of inherited potential; an omitted teaching invitation never blocks an ordinary practice.

## What succession carries

The word “parent” denotes an input provenance profile. It does not mean every route is biological reproduction. “Cross-breed” in this workbench means combining two selected synthetic profiles under the displayed experimental policies. The four channels stay distinguishable in each trait and trace:

| Channel | Transmitted record | One contributing parent | Both contributing parents | What the record does |
|---|---|---|---|---|
| Biological | Experimental compatibility potential | Gate 3/4 | Gate 7/8 | Records a potential candidate; no real gene or active axis |
| Resonant | Experimental resonant potential | Gate 1/2 | Gate 3/4 | Records a separate potential route without assuming biology |
| Cultural / mentorship | Teaching invitation or curriculum provenance | Gate 1/2 | Gate 1/1 | Suggests where instruction could be sought; copies no mastery |
| Fabricated / blueprint | Ordinary drawing or compatibility specification | Gate 3/4 | Gate 1/1 | Preserves design provenance; fabricates and installs nothing |

These fractions are chosen fixture thresholds, not measured rates. Each trait uses a SHA-256 hash of the ruleset digest, selected parent records, seed, and trait ID, reduced modulo its policy denominator. The trait passes when the draw is below the numerator. The complete decision is returned in `trace`. There are no hidden rerolls or mutations and no spontaneously introduced traits. Changing a seed explores another deterministic fixture outcome, not an empirical prediction.

The output records an inherited trait once even if both parents contribute it. Its provenance names every immediate contributing parent, their generation, the earlier lineage ID where applicable, and deduplicated original founder records. A child can retain zero, one, or both axis potentials. The two potential flags are computed separately from retained axis-bearing traits. A cultural route cannot carry axis potential.

Every output has `status: EXPERIMENTAL`, `learned_skills: []`, and both entries of `active_axis_access` set to `unavailable`. It contains no installed equipment, growth points, focus, or charge. Applying a lineage in the workbench creates the separately specified new-incarnation state; it does not convert potential into availability.

## Catalog and branching

`data/lineages.json` supplies eight synthetic profiles: `ordinary-learner`, `archive-keeper`, `affinity-potential`, `techfinity-potential`, `dual-potential`, `mentorship-conductor`, `fabricated-successor`, and `mixed-route-candidate`. They cover zero, one, and two-axis source profiles plus all four provenance channels. The labels describe test records, not canonical populations.

Each generated output contains one selected progression-route suggestion and four inspectable interaction branches:

| Interaction | Candidate conditions | Suggested experiment |
|---|---|---|
| Taught spell + ordinary drawing | Retain spell mentorship and ordinary lamp blueprint | Ordinary magic with ordinary technology; no axis required |
| Affinity potential + ordinary drawing | Retain Affinity potential and ordinary lamp blueprint | Affinity expression with an ordinary device procedure |
| Taught spell + Techfinity potential | Retain spell mentorship and Techfinity potential | Ordinary spell procedure with a Techfinity expression |
| Independent expression pairing | Retain both potentials | Learn and execute Woven Beacon after supplying both active access facts |

The status is `CANDIDATE` or `BLOCKED`, with exact missing trait/potential references. Candidate status is advisory and grants no gameplay effects. `skill_candidates` lists existing approved node IDs; it is not an unlock list. The first three composition patterns remain boundary-test variants of the skill model; this module installs no extra graph nodes. The fourth points at the approved H1 recipe. Training, growth costs, actual axis availability, equipment, activation costs, and recovery are still checked by the skill engine.

The readable diagrams are `hereditary-pathways.mmd` and `multigeneration-pathway.mmd`. The executable counterpart is `data/hereditary-pathways.json`: four concrete zero/one/two-axis cases and the complete two-generation outputs. The diagrams express data and progression relationships, never canonical containment.

## Exact interfaces

```python
from pathlib import Path
from starweaver.heredity import load_catalog, generate_lineage, extend_catalog

catalog = load_catalog(Path("data"))
first = generate_lineage(catalog, "affinity-potential", "techfinity-potential", "trial-1")
with_first = extend_catalog(catalog, first)
second = generate_lineage(with_first, first["id"], "archive-keeper", "generation-two")
```

`load_catalog(data_dir: Path) -> dict` reads `lineages.json` with a one-MiB read bound and validates it. `generate_lineage(catalog: dict, parent_a: str, parent_b: str, seed: str) -> dict` returns plain JSON data without changing the catalog. It requires two distinct registered IDs and a printable, nonblank seed of 1–80 characters. Unicode seeds are supported. A reciprocal cross retains the same trait selection, but its parent slot order and output ID remain distinct and inspectable.

`extend_catalog(catalog: dict, lineage: dict) -> dict` recomputes the complete expected output from its parent IDs and seed, then compares every derived field. Only an exact output can register a generated parent. Registration returns a deep copy. Re-registering the same verified output is idempotent. The added profile is:

```text
{
  id: lineage.id,
  label: "Generation N · <ID suffix>",
  description: "Registered experimental generation; potential and provenance only.",
  traits: [retained trait IDs],
  generation: N,
  source_lineage: <complete verified output>
}
```

Built-ins have generation zero and `source_lineage: null`. Generated snapshots contain flat ancestor IDs, immediate parent trait references, and original founder origins; they do not embed parent snapshots. The catalog registry preserves the earlier snapshots in topological registration order. Validation replays them once each, rather than recursively traversing copied ancestors. Unknown parents, forward references, cycles, altered traits, altered access, changed trace decisions, added equipment, and fabricated snapshots are rejected. A caller-supplied opaque ID is not treated as proof.

There are at most 30 registered generations, generation depth is at most 30, each snapshot is at most 256 KiB, and the expanded catalog is capped at four MiB with at most 128 total profiles and 24 trait definitions. The current fixture uses eight trait definitions and eight base profiles. The reference 30-generation chain stays below 30,000 JSON characters per output. These are bounded fixture limits, not metaphysical limits on lineage.

Malformed requests raise `LineageError`, a `ValueError` subclass. File I/O errors remain ordinary I/O exceptions. Objects are closed: extra fields are invalid. References, policy fractions, duplicate JSON keys, booleans masquerading as integers, and generated ancestry are checked before use. `schemas/lineage.schema.json` describes both the lineage output and `#/$defs/catalog`; the runtime also enforces exact recomputation and constraints that JSON Schema alone cannot express.

## Reproducible two-generation example

With the checked-in rules and data:

1. Cross `affinity-potential` with `techfinity-potential`, seed `trial-1`. The result is `lineage-a2be071d5c4f750d7c0d`, with biological Affinity potential and the Techfinity interface specification. Both potential flags are true; active access is unavailable for both.
2. Recompute and register that exact output.
3. Cross that generated parent with `archive-keeper`, seed `generation-two`. The result is `lineage-2d666f674325211e742e`. It retains the biological Affinity candidate and interface specification from generation 1, with the original `affinity-potential` and `techfinity-potential` founders still named. It also retains a spell mentorship invitation directly from `archive-keeper`.
4. Registering or applying either output still grants no learned rank, active axis access, or equipment. A later incarnation can learn ordinary skills and must receive axis access through a separately supplied scenario fact before learning expressions.

The checked-in pathway fixture contains the full outputs, including all successful and failed trait gates, candidate/blocked interaction branches, and provenance. Tests regenerate those records instead of trusting their labels.

## Verification and evidence limits

From the `star-weaver` directory, run `python -m unittest discover -s tests -p test_heredity.py -v`. The suite exercises deterministic outputs; reciprocal crosses; zero/one/two-axis outcomes; ordinary and one-axis interactions; non-spontaneous traits; parent/founder attribution; teaching versus potential; generation replay and merged ancestry; input rejection; tampered snapshot rejection; a 30-generation bound; and catalog immutability. Integration, persistence, and real browser journeys belong to the server/workbench verification receipt.

Implementation and deterministic succession are executable. Hereditary world laws and creative fit remain experimental decisions for Joshyua; this software cannot establish them through simulation.
