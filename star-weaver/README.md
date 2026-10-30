# Star Weaver

A local workbench for Starweaver’s Matrix: learn and exercise the approved five-node skill graph, observe composed effects and interruption, and explore reproducible cross-breed hereditary branches across multiple generations.

## Open it

On Windows, double-click **Start Star Weaver.cmd**. Python 3.10 or newer is required; the launcher reuses the local Codex Python bundle when present and otherwise uses Python on the current command path. No packages need to be installed. Keep the launch window open while using the workbench.

On any supported desktop:

```sh
python server.py --open
```

Open <http://127.0.0.1:8765>. The server binds only to loopback. If that port is occupied, use `python server.py --port 8766 --open`. Close the launch window or press Ctrl+C to stop it.

## Skill loop

Select a node, learn it, and activate it. Advance the model with **Next tick**. Learn M0 and T0, then A1 and T1, then H1. The five-node route uses six growth points. Woven Beacon costs one focus and one charge, completes after two ticks, and recovers for two more ticks. Its source inputs share that recovery lock.

The scene renders ordinary light, guided light, signal control, and the composed beacon from actual execution state. Turning off Techfinity or removing the lamp during a beacon aborts the action: no beacon output, no refund of committed resources, and no loss of learned ranks. The resource refill and access toggles are explicitly sandbox controls.

## Lineage and cross-breed paths

The lineage workbench uses synthetic profiles with biological, resonant, cultural/mentorship, and fabricated/blueprint provenance routes. The latter two are succession routes, not biological crossbreeding. Select two profiles and a seed to generate a deterministic offspring, inspect trait-level contributions and available branches, and export the full lineage JSON. **Keep as parent** adds it to the parent list for another generation. **Use as new incarnation** starts that lineage with zero learned ranks, no equipment, and both axes unavailable. Potential never becomes skill ownership or active access automatically.

The engine keeps the branch-specific policies, not universal genetics, explicit and editable in `data/lineages.json`. These new hereditary policies are **EXPERIMENTAL**. See [heredity rules and pathways](docs/heredity.md), the [lineage schema](schemas/lineage.schema.json), and the diagrams under `docs/`.

## Save and recovery

Every successful action is saved atomically in `runtime/session.json`; the previous validated save is retained as `runtime/session.bak.json`. The workbench resumes it when reopened, including an active action's discrete tick state. Time advances only through the tick control. Export creates a portable JSON backup. Import validates the whole snapshot before replacing the current session. Import and reset start a bounded request-history epoch while keeping the session revision increasing. A stale browser receives a conflict response and refreshes its view without replaying the action.

The confirmed **Reset practice scenario** action also clears registered generated parents and starts a fresh lineage registry. Export first to keep a portable copy of those branches. This is the recovery route when the 30-parent registry or request history is full.

Damaged local saves are preserved separately; if a valid previous backup exists, it is recovered and a notice is shown. Runtime saves are ignored by Git. Do not run multiple server instances against the same runtime directory; use `--state-dir` for an isolated session or test.

## Decisions and evidence

Joshyua approved SW-SKILL-001 for implementation in the originating chat on October 22, 2026 and requested the GitHub upload. [The approved baseline](docs/approved-baseline.md) preserves the original proposal text. [Decision metadata](data/decisions.json) records implementation approval separately from source canon and the new experimental hereditary policy.

Affinity and Techfinity remain independent system references. Finity remains Context Doubt with no runtime gate, rank, resource, or hierarchy. New profile names do not name canonical species or bloodlines. No private Notion source dump, personal lineage data, or credentials are included.

This module coexists with the repository's root Think Tank app and iOS prototype; neither is a dependency of this workbench.

## Verify

```sh
python -B verify.py
```

This runs the application tests and refreshes `verification/unit-results.json`.

PowerShell 7 can also validate the formal skill data:

```powershell
Test-Json -Path data/star-weaver.fixture.json -SchemaFile schemas/star-weaver.schema.json
```

Tests exercise the actual engine, typed composition inputs, independent progression, resource transactions, refund behavior, save/import boundaries, local HTTP flows, and deterministic lineage generation. Browser QA evidence is recorded in `verification/`. Tests use isolated synthetic state. Human assessment of feel/readability/balance and full MAGECH kernel conformance remain separate from technical execution.
