# MIRA Old-Game Remaster Factory: Milestones & Goal Prompts

Target experience: take an older game or small RPG-like slice, extract gameplay traces and legal
assets/state where available, then produce an editable remaster package with explicit gameplay
rules, object state, neural visual upgrading, replay tests, and a lightweight runtime.

This is not a plan to replace the original engine with a pixel-only video model. The practical
version is a **hybrid neural/symbolic remaster engine**:

- explicit mechanics graph for combat, traversal, inventory, quests, collision, save/load, and
  scripted state;
- object-centric state for persistent entities such as doors, chests, NPCs, enemies, pickups, and
  quest objects;
- neural world model / renderer for visual continuation, animation cleanup, relighting, material
  detail, style transfer, and uncertain residual dynamics;
- adapters for per-game mechanics, remaster styles, and optional new modded mechanics;
- exportable runtime package with schemas, tests, tools, and checkpoints.

The output should look more like an editable game package than a single checkpoint:

```text
remaster_project/
  state_schema/
  mechanics_graph/
  entity_database/
  quest_graph/
  neural_renderer/
  style_adapter/
  physics_adapter/
  modding_api/
  test_replays/
```

Each milestone lists: **Goal**, **Why it's ordered here**, **Deliverables**, and a **Goal Prompt**
you can hand directly to an agent/engineer.

---

## R0 - Choose a legal, instrumentable prototype game

**Goal:** Pick the first target where capture, state access, asset use, and redistribution are
practical.

**Why first:** The project succeeds or fails on observability and rights. A famous closed RPG may be
conceptually attractive but can block capture automation, asset reuse, mod APIs, and demo sharing.

**Good first targets:**
- an open-source or permissively licensed 3D game;
- a small Unity/Godot RPG slice where instrumentation can be added;
- an OpenMW/Morrowind-style area with accessible state and modding tools;
- a homebrew Zelda-like or Soulslike test map with one town, one dungeon, and one combat loop.

**Deliverables:**
- Target selection memo with license/ToS assessment, source availability, asset rights, mod/debug
  API access, deterministic replay feasibility, and redistribution constraints.
- Scope cut: one area, one traversal loop, one interaction loop, one combat loop, one menu loop.
- Success criteria for the first remastered slice: trace replay, object persistence, visual
  upgrade consistency, editable mechanic, and runtime export.

**Goal Prompt:**
> Select the first old-game remaster prototype target. Compare at least three candidates on legal
> status, instrumentation access, asset availability, replay determinism, and demo-shareability.
> Recommend one small slice and write a target selection memo with the exact loops to remaster,
> the state we can observe, the assets we can legally use, and the constraints that must shape all
> later milestones.

---

## R1 - Capture traces and extract state/assets

**Goal:** Build a repeatable extraction pipeline that records frames, inputs, state, events, save
snapshots, and reusable assets for the selected slice.

**Why here:** The neural parts need pixels and actions; the remaster runtime needs structured state
and assets. If state is missing now, later milestones either hallucinate hidden logic or become
unverifiable.

**Deliverables:**
- Fixed-fps gameplay video with synchronized controller/keyboard input.
- State traces where available: camera pose, player pose, health/stamina, inventory/equipment,
  quest flags, enemy/NPC state, object IDs, animation state, collision/navmesh references, and
  save checkpoints.
- Event labels: menu, dialogue, cutscene, loading, death/respawn, combat start/end, item pickup,
  door/chest state change, quest progression.
- Asset extraction manifest for legal assets: maps, meshes, textures, sprites, animations, audio,
  scripts, and localization strings.
- MIRA-compatible dataset shard/index format plus a richer sidecar for remaster-specific state.

**Goal Prompt:**
> Implement the trace extraction pipeline for the selected prototype. Record fixed-fps video,
> synchronized input, state snapshots, event labels, save checkpoints, and a legal asset manifest.
> Produce MIRA-compatible shards plus remaster sidecars, then validate by loading random clips,
> replaying state timelines, and rendering a debugging view that overlays object IDs and events on
> top of captured frames.

---

## R2 - Define the remaster state schema

**Goal:** Convert raw traces into a versioned, object-centric schema that can drive mechanics,
tests, editing tools, and neural conditioning.

**Why here:** Remastering needs stable handles. "Door stayed open" and "NPC remembers the quest"
are state-schema problems before they are model problems.

**Deliverables:**
- `GameObject` schema with stable ID, class, pose, bounds/collision token, animation state,
  interaction affordances, visibility, material/style token, and persistent state.
- Player and camera schemas: pose, velocity, input, equipment, health/stamina/mana, lock-on target,
  current mode, and save/load metadata.
- Quest/dialogue/inventory schemas appropriate to the prototype scope.
- Dataset migration/versioning rules so future extra fields are additive and old traces remain
  loadable.
- Tests that round-trip traces through the schema and preserve stable object IDs across clips.

**Goal Prompt:**
> Design the remaster state schema for the prototype slice. Normalize extracted traces into stable
> object, player, camera, inventory, quest, dialogue, and event records. Add schema versioning and
> round-trip tests. Prove that persistent objects keep stable IDs when they leave the camera view,
> re-enter later, or change state.

---

## R3 - Recover an explicit mechanics graph

**Goal:** Build an executable, inspectable rules layer for the slice's gameplay: combat,
traversal, inventory, object interaction, quests, and save/load.

**Why here:** A remaster must be testable and moddable. Hidden mechanics should not live only in a
latent video model.

**Deliverables:**
- Mechanics graph representation: typed nodes, state reads/writes, conditions, effects,
  priorities, timers, cooldowns, and event emission.
- First rules: movement/collision, door/chest interaction, item pickup, health/stamina changes,
  one combat exchange, one quest flag update, one menu transition.
- Rule recovery workflow: combine source/mod scripts when available, state-trace mining, manual
  annotation, and learned rule suggestions.
- Deterministic simulator that advances structured state from input and prior state.
- Unit tests and trace-replay tests comparing predicted state changes against captured traces.

**Goal Prompt:**
> Implement the first executable mechanics graph for the remaster slice. Start with movement,
> interaction, one combat loop, one inventory/menu transition, and one quest flag update. Build
> replay tests against captured traces and report every mismatch as either a missing rule,
> incorrect parameter, missing state field, or nondeterministic original-game behavior.

---

## R4 - Train a neural remaster renderer

**Goal:** Learn to convert old-game frame/state/assets into a consistent upgraded presentation.

**Why here:** This is the part that makes the output feel like a remaster rather than an emulator
or trace viewer. It should remain conditioned by explicit state instead of inventing gameplay.

**Deliverables:**
- Renderer conditioning contract: old frame, camera, object state, material/style tokens, optional
  source asset references, and target style prompt or adapter ID.
- Baselines: super-resolution/upscaling, texture replacement, frame-to-frame video enhancement,
  and state-conditioned neural renderer.
- Metrics: temporal consistency, object identity preservation, HUD/text legibility, input/action
  latency, and side-by-side trace replay fidelity.
- First style adapter: "faithful remaster" before more aggressive modernized styles.

**Goal Prompt:**
> Train the first neural remaster renderer for the prototype slice. Condition it on old frames,
> camera/object state, and legal asset references. Compare it to simpler upscaling and texture
> replacement baselines. Ship a faithful-remaster style adapter with temporal consistency,
> identity preservation, HUD/text, and trace-replay metrics.

---

## R5 - Add a state-conditioned world model for visual dynamics

**Goal:** Add MIRA-style latent prediction for animation continuity, camera motion, interaction
appearance, and uncertain residual dynamics, while the mechanics graph remains authoritative.

**Why here:** The renderer can upgrade known frames; the world model is needed when the remaster
runtime is played interactively and must synthesize future frames from state and input.

**Deliverables:**
- Training config that consumes past frames, input, explicit state, event tokens, and future
  frames/state deltas.
- Action/state conditioning path: input affects mechanics first, mechanics emits state deltas, the
  neural model renders the next visual continuation.
- Metrics: action-swap divergence, state-swap correctness, object persistence, off-camera re-entry,
  loop/revisit consistency, and long-rollout drift.
- Ablation: pixel/action-only world model vs. state-conditioned world model.

**Goal Prompt:**
> Train a state-conditioned MIRA-style world model for the remaster slice. The mechanics graph is
> authoritative for state updates; the neural model predicts visual continuation from past latents,
> input, state, and events. Compare against a pixel/action-only baseline and show whether explicit
> state improves persistence, interaction fidelity, and replay consistency.

---

## R6 - Build mechanic and style adapters

**Goal:** Make the system editable without full retraining: freeze the base model where possible
and add adapters for mechanics, interaction modes, and visual styles.

**Why here:** A remaster factory needs repeatable customization: faithful mode, modern graphics,
new traversal ability, altered combat timing, or a modded encounter.

**Deliverables:**
- Adapter interface for visual style, combat timing, traversal mode, inventory/menu rendering, and
  object interaction.
- First mechanics adapter: change one scoped rule, such as dodge timing, climbing stamina, door
  interaction timing, or weapon reach.
- First style adapter: faithful remaster vs. modernized lighting/materials.
- Regression suite proving adapters do not break unrelated mechanics or object persistence.

**Goal Prompt:**
> Add adapter support to the remaster runtime. Implement one visual style adapter and one mechanic
> adapter over a narrow gameplay loop. Demonstrate that an editor can enable/disable each adapter,
> replay the same trace, and see the intended change without unrelated quest, inventory, collision,
> or persistence regressions.

---

## R7 - Create the editor and modding surface

**Goal:** Expose the remaster package as something designers can inspect and edit, not just run.

**Why here:** The strongest use case is game archaeology -> remaster -> modding. The model should
be a gameplay prior and renderer inside a tool, not an opaque output.

**Deliverables:**
- Entity browser with object IDs, state, class, pose, affordances, and linked assets.
- Mechanics graph editor or declarative rule files with validation.
- Trace viewer comparing original frame, remastered frame, state, events, and rule effects.
- Modding API for adding/editing objects, encounters, item stats, dialogue branches, and simple
  quest flags.
- Safety checks: puzzle solvability constraints, unreachable object checks, invalid quest graph
  transitions, and replay-test selection.

**Goal Prompt:**
> Build the first remaster editor for the prototype package. It must let a user inspect entities,
> edit a small mechanics graph, tweak one encounter or interaction, run the affected trace tests,
> and preview original vs. remastered playback. Prioritize verifiable edits over broad creative
> freedom.

---

## R8 - Export a lightweight playable runtime

**Goal:** Package the remaster as a portable runtime bundle with explicit state, mechanics,
adapters, renderer/world-model checkpoints, assets, and tests.

**Why here:** "Packability" is the key product claim. The output must be movable and testable,
not just a training run.

**Deliverables:**
- Runtime loop: input -> mechanics/state -> neural renderer/world model -> frame/audio/UI.
- Save/load format that serializes explicit state, adapter selection, RNG seeds, and model context.
- Replay runner for original traces and modded traces.
- Runtime bundle manifest with versioned schemas, checkpoints, assets, and dependency constraints.
- Performance profile with latency breakdown and minimum hardware target.

**Goal Prompt:**
> Export the prototype remaster as a lightweight runtime bundle. Include schemas, mechanics graph,
> entity database, legal assets, renderer/world-model checkpoints, adapters, replay tests, and a
> manifest. Implement save/load and deterministic replay for the explicit state path. Profile
> runtime latency and document what would be required to ship a browser or low-end desktop demo.

---

## R9 - Validate fidelity, mod safety, and remaster quality

**Goal:** Prove that the remaster remains faithful where it should, editable where intended, and
stable during play.

**Why here:** The hard part is preserving causal structure, not just producing nicer frames.

**Deliverables:**
- Golden-path quest tests: start, progress, completion, failure, and save/load around key states.
- Combat tests: damage, dodge/parry timing, hitboxes, cooldowns, invulnerability windows, enemy
  death, rewards, and state cleanup.
- Object persistence tests: doors, chests, pickups, NPC movement, destroyed objects, and off-camera
  re-entry.
- Visual tests: style consistency, temporal stability, HUD/text readability, animation continuity,
  and object identity preservation.
- Mod safety tests: edited encounters remain reachable, puzzles remain solvable, quest graph stays
  valid, and unrelated mechanics do not regress.

**Goal Prompt:**
> Build the validation suite for the remaster slice. Cover quest flow, combat timing, interaction
> state, object persistence, save/load, visual quality, and mod safety. Produce a scorecard that
> separates original-game fidelity, remaster visual quality, runtime performance, and editability.

---

## R10 - Scale from slice to remaster pipeline

**Goal:** Generalize the prototype into a reusable pipeline for additional areas, games, and
remaster styles.

**Why here:** Only after one slice works end to end should the project invest in broader
automation.

**Deliverables:**
- Multi-area ingestion with shared schemas and per-area manifests.
- Game/profile registry for extraction hooks, schema mappings, mechanics plugins, and adapters.
- Foundation model strategy: shared game/video world model plus per-game control and style
  adapters.
- Cost model for capture hours, annotation, training, QA, and runtime performance.
- Recommendation on which class of old games should be targeted next.

**Goal Prompt:**
> Turn the working prototype into a reusable remaster pipeline. Add a game/profile registry,
> multi-area ingestion, shared schema contracts, adapter training recipes, and cost estimates.
> Recommend the next target class based on observability, legal safety, automation potential,
> visual payoff, and how much of the mechanics graph can be recovered automatically.

---

## Suggested ordering

```text
R0 -> R1 -> R2 -> R3 -> R4 -> R5 -> R6 -> R7 -> R8 -> R9 -> R10
```

R3 and R4 can overlap once R2 is stable. R7 can start as a trace viewer during R1/R2, but should
not become a full editor until the mechanics graph and renderer have something reliable to edit.

## Cross-cutting principles

- **Explicit beats implicit for correctness:** rules, state, save/load, quests, and collision should
  be inspectable whenever possible.
- **The neural model is a renderer and dynamics prior:** use it for visual richness, animation
  continuity, and uncertain residuals, not as the only owner of hidden game logic.
- **Preserve trace provenance:** every generated training sample should be traceable back to source
  footage, input, state, event labels, extraction settings, and license constraints.
- **Regression tests are product features:** replay tests, quest tests, combat tests, and mod-safety
  tests are what make the output remasterable rather than merely impressive.
- **Start smaller than the dream:** prove one town/dungeon/combat slice before trying famous,
  closed, large open-world RPGs.
