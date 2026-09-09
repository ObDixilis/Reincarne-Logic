# GORGON Game Studio Runtime — Agent Contract v0.1

## Mission
Build playable Reincarne game prototypes with the smallest sufficient agent/model/tool stack, while preserving canon, IP boundaries, reproducibility, and user attention.

The first milestone is **Magic Sandbox Alpha**: a pitch-quality combat testbed for contextual, compositional magic inspired by the *interaction grammar* of older four-player action games, but implemented as original Reincarne/GORGON IP.

## Authority and source-of-truth hierarchy
1. **User direction in the active task** — highest execution authority.
2. **Notion: GORGON Compiler Architecture — Control Plane v1.0** (`GCA-CONTROL-PLANE-001`) — architecture/governance source.
3. **Notion canonical world/IP records** — narrative and ontology authority.
4. **This repository** — machine-executable implementation truth: code, configs, tests, docs, CI.
5. **Google Drive: GORGON Game Studio Runtime** — large assets, references, captures, packaged builds.
6. External documentation/open-source repositories — evidence or dependencies only; never silently become canon.

When sources conflict, preserve the conflict and route it through Context Doubt. Do not silently choose a convenient interpretation.

## Frozen architecture rules
- MAGECH Kernel v1.3 + Freeze Charter v1.0 is FROZEN.
- Do not invent a new MAGECH primitive because implementation is difficult.
- Try existing composition, parameters, contracts, and `UNRESOLVED` before proposing ontology expansion.
- KINETIC//LANGUAGE remains the combat/action-language realization layer.
- Game-Forge may realize gameplay/events without absorbing MAGECH or KINETIC//LANGUAGE.
- New runtime abstractions are implementation-level by default unless proven otherwise.

## Runtime design principle
The game must run deterministically without waiting on an LLM in the per-frame combat loop.

AI may assist development, authoring, testing, balancing, documentation, telemetry analysis, and offline content synthesis. Any runtime generative-AI feature requires explicit user approval and a latency/fallback/privacy contract.

## Execution-budget policy
Use the smallest sufficient stack.

### Default routing
- trivial search, rename, documentation cleanup, file inspection → low-cost/fast model
- routine implementation, tests, refactors with clear local scope → standard coding model
- cross-module Unreal integration, networking, systemic debugging → stronger reasoning model
- architecture deadlocks, major migrations, unresolved multi-system failures → Astra-class escalation

### Escalation gate
Escalate only when at least one is true:
1. two bounded lower-cost attempts failed;
2. the decision changes architecture across multiple systems;
3. the task requires large-context reconciliation that cannot be safely partitioned;
4. correctness risk is high enough that a cheap failure would cost more than escalation.

Do not use maximum reasoning for routine work.

## Scope discipline
Every substantial task must define:
- Outcome
- Constraints
- Inputs / relevant files
- Acceptance criteria
- Explicit non-goals
- Verification method
- Stop condition

Do not refactor unrelated code, scan unrelated repositories, regenerate working assets, or redesign adjacent systems unless required by an acceptance criterion.

## Checkpoint policy
Prefer small reversible milestones.

`plan → implement core → compile → test → playtest → repair → package → document`

Checkpoint after each materially working stage. Never leave the branch knowingly broken when a known-good checkpoint is available.

## Open-source intake policy
External code is **reference until cleared**.

Before adopting a dependency or copying meaningful implementation:
1. record repository/source URL;
2. identify exact license and version/commit;
3. assess compatibility with intended commercial distribution;
4. inspect maintenance/quality/security posture;
5. prefer existing engine/native capability when equivalent;
6. isolate third-party code behind an adapter where practical;
7. add required notices/attribution;
8. test independently before coupling to core gameplay.

Preferred default licenses: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, or similarly permissive licenses after verification.

Do not import GPL/AGPL/LGPL, source-available, non-commercial, research-only, or unclear-license code into shipping code without an explicit compatibility decision.

## Unreal architecture rules
- Prefer data-driven abilities/interactions over one-off hard-coded spell classes.
- Use Gameplay Tags or equivalent semantic identifiers for state and interaction contracts.
- Separate simulation/gameplay consequence from VFX/audio presentation.
- Server/authoritative simulation must produce the gameplay result; presentation interprets it.
- Preserve deterministic or reproducible resolution wherever multiplayer requires it.
- Expensive environmental/interaction queries must have explicit budgets.

## Magic-system grammar
Conceptual event shape:

`Source × Verb × CasterState × Motion × TargetState × AllyState × WorldState × Modifiers → ResolvedGameplayEvent`

This is a grammar, not a mandate that every axis participate in every ability.

Rules:
- avoid N×N hand-authored reaction tables when a smaller consequence grammar can express the behavior;
- keep reactions readable enough for players to infer cause and effect;
- every powerful interaction needs cost, counterforce, limit, recovery, residue, or another meaningful constraint;
- test interaction order, stacking, cancellation, ownership, replication, and cleanup explicitly.

## Prototype-content boundary
Temporary test concepts such as `Test.Fire`, `Test.Wind`, `Test.Water`, and `Test.Lightning` may be used to validate mechanics, but they are **NON-CANON implementation fixtures** until mapped through existing Reincarne/MAGECH vocabulary.

Do not promote a test fixture into canon by naming coincidence.

## Blender / asset rules
- Favor non-destructive and procedural workflows where practical.
- Keep source `.blend` assets separate from Unreal imports/exports.
- Preserve scale, axis, skeleton, naming, and export presets in project documentation.
- AI-generated or third-party assets require provenance notes before promotion beyond prototype status.

## Testing minimum
For each systemic mechanic, include where feasible:
- unit/data validation
- interaction test
- multiplayer/ownership test when relevant
- cleanup/lifetime test
- performance sanity test
- a human-playtest acceptance case

A feature is not complete because it compiles.

## Agent completion contract
Return only what the user needs to judge the milestone:
1. playable/build result or exact reason it is blocked;
2. changed files/systems;
3. verification performed and results;
4. unresolved risks or canon questions;
5. next recommended milestone.

Do not bury blockers in a long progress narrative.
