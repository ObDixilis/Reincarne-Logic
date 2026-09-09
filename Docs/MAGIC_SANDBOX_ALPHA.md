# Magic Sandbox Alpha — Vertical Slice Contract v0.1

## Purpose
Create a small playable sandbox that demonstrates the core value proposition of the Reincarne combat-magic engine: **contextual magic as a compositional language**, not a menu of isolated spells.

This is a systems prototype, not a content-complete game.

## Player-facing pitch
Four players enter a compact arena with distinct test loadouts. Their abilities alter targets, movement, fields, and environmental state. The fun comes from discovering how one player's action changes what another player's action becomes.

## Success criteria
A successful Alpha allows a player to:
1. move, jump, attack, dodge, and cast reliably;
2. use at least four non-canon test Sources/affinities purely as mechanic fixtures;
3. trigger materially different ability outcomes based on caster/target/world state;
4. create at least three readable cooperative interaction chains involving two or more players;
5. understand why an interaction happened from animation/VFX/audio/gameplay consequences;
6. reset the arena and repeat tests quickly;
7. run without an LLM dependency in the frame-to-frame combat loop.

## Non-goals
- final character art
- final Reincarne canon naming
- campaign/story content
- complete progression system
- production matchmaking/backend
- monetization
- huge open world
- exhaustive spell catalogue

## Recommended technical substrate
Prototype in Unreal Engine using the Gameplay Ability System or a comparable data-driven ability architecture, Gameplay Tags for state contracts, Enhanced Input, Niagara for presentation, and multiplayer-capable authoritative gameplay logic.

The implementation should avoid coupling the conceptual system to any single presentation effect.

## Minimal interaction vocabulary
These are implementation fixtures only.

### Source fixtures
- `Test.Fire`
- `Test.Wind`
- `Test.Water`
- `Test.Lightning`

### Verb fixtures
- `Verb.Project`
- `Verb.Field`
- `Verb.Lift`
- `Verb.Impulse`
- `Verb.Saturate`
- `Verb.Ignite`
- `Verb.Conduct`

### State fixtures
- `State.Airborne`
- `State.Wet`
- `State.Burning`
- `State.Charged`
- `State.InWindField`
- `State.Comboing`

### World fixtures
- `World.Flammable`
- `World.Conductive`

## Interaction examples
These examples validate the grammar and are not automatically canon.

### A. Wind lift + projectile redirection
1. Player A creates a Wind field with Lift.
2. Targets gain `State.Airborne` and/or occupy the field.
3. Player B sends a projectile through the field.
4. Resolver modifies trajectory/impulse according to field direction.

Test value: ally-state/world-state influence on an existing cast.

### B. Saturation + lightning conduction
1. Player A applies Saturate to enemies or terrain.
2. Player B applies Lightning.
3. Conductive propagation extends to valid nearby wet targets with bounded range/chain count.

Test value: state-driven propagation with explicit limits.

### C. Burning + wind pressure
1. Fire establishes burning/heat consequence.
2. Wind applies directional pressure.
3. Burning effect is displaced, intensified, spread, or shortened according to a deterministic rule.

Test value: consequence grammar rather than a hard-coded named combo.

## Resolver contract
A cast should produce a normalized interaction request conceptually shaped like:

```yaml
CastEvent:
  source: Test.Fire
  verbs: [Verb.Project]
  caster_states: []
  target_states: []
  ally_fields: []
  world_states: []
  modifiers: {}
```

The resolver returns gameplay consequences rather than only a named spell:

```yaml
ResolvedGameplayEvent:
  damage: 0
  impulse: null
  states_added: []
  states_removed: []
  spawned_fields: []
  propagation: null
  cost: null
  residue: []
  presentation_cues: []
```

## Readability constraints
- Every interaction must have a visual onset, consequence, and decay/readout.
- Four-player overlap cannot become an opaque particle cloud.
- Presentation priority should favor actionable gameplay state over decorative effects.
- Strong interactions require stronger anticipatory/impact cues.

## Economy constraints
Every major interaction should expose at least one meaningful limit such as:
- resource cost
- cooldown
- field lifetime
- propagation cap
- range
- setup requirement
- recovery window
- counter-state

Avoid free recursive loops.

## Alpha arena
Use one compact graybox arena with:
- central open combat floor
- elevated ledges for airborne testing
- one flammable test zone
- one conductive/wettable test zone
- enemy spawn/reset controls
- debug HUD/state visualization toggle

## Test actors
Start with simple capsules/mannequins and obvious team colors or identifiers. Art quality is not an Alpha acceptance criterion.

## Required debug tools
- display active gameplay/state tags on selected actor
- show last resolved interaction and contributing inputs
- reset actors/world state
- spawn test enemies
- optionally slow simulation for interaction inspection

## Multiplayer progression
Implementation order:
1. deterministic single-player resolver
2. local multi-actor simulation
3. two-player network validation
4. four-player validation

Do not begin by debugging four-player networking and the interaction ontology simultaneously.

## Completion gate
Alpha is pitchable when a user can play for 10–15 minutes and independently discover at least three interaction chains without developer intervention, while the debug tooling proves that the resulting state transitions are deterministic and bounded.

## Next milestone after Alpha
**Magic Sandbox Beta:** map successful test fixtures into existing Reincarne/MAGECH vocabulary, improve character movement/combat feel, establish visual-language rules, and validate four-player readability/performance.
