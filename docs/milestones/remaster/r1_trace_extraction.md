# R1 — Capture Traces and Extract State/Assets

**Objective:** a repeatable extraction pipeline for the R0 slice: fixed-fps video, synchronized
input, structured state snapshots, event labels, save checkpoints, and a legal asset manifest —
emitted as MIRA-compatible shards plus a richer remaster sidecar.

## 0. Context & prerequisites

- **Depends on:** R0 memo (target, rights constraints, slice definition).
- **Reuses:** the RPG-track M2 capture harness architecture (video+JSONL+meta, sync measurement,
  shard builder, chunking, annotation events) — R1 should be a *profile* of that pipeline, not a
  second implementation. Where the R0 target's engine gives direct state access (open source /
  mod API), R1's state taps are far richer than M2's Tier-1 OCR.

## 1. Design

### 1.1 Recording layer

- Fixed-fps video + per-frame input JSONL (M1 format: buttons + axes if applicable) + session
  metadata, exactly the M2 contract → the shards load through the standard mira dataset API.
- Engine-side instrumentation (the R0 target was chosen for this): a per-frame state logger
  emitting `state.jsonl` — camera pose, player pose/velocity, health/stamina, inventory,
  equipment, quest flags, enemy/NPC state (pose, AI state, target), object registry rows
  (stable engine ID, class, pose, animation state, interactable flags), collision/navmesh refs,
  and RNG seeds where exposed.
- Save checkpoints: engine save files snapshotted at session start/end and at scripted intervals;
  named and referenced from `meta.json`.

### 1.2 Event labels

On the shared match clock (generic `Event` type): menu, dialogue, cutscene, loading,
death/respawn, combat start/end, item pickup, door/chest state change, quest progression. With
engine access these come from instrumentation hooks (exact), falling back to M2-style detectors
only where hooks are missing.

### 1.3 Asset extraction manifest

- Inventory of legally usable assets: maps, meshes, textures, sprites, animations, audio,
  scripts, localization strings — with per-asset provenance and license terms from the R0 memo.
- Extraction into documented interchange formats (glTF, PNG, OGG…) with a manifest JSON:
  `{asset_id, type, source_path, license, allowed_uses, sha256}`. The manifest is the single
  authority later milestones consult before using an asset for training or shipping.

### 1.4 Output layout

- **MIRA shards** (`n_players=1`) + `index.json`: video/actions for neural training (R4/R5).
- **Remaster sidecar** per chunk: `state.jsonl`, event list, save refs — schema-v2 opaque payload
  now; R2 will formalize it.
- Raw sessions archived immutably (provenance principle: every training sample traceable to
  source footage, input, state, extraction settings, license constraints).

## 2. Phased execution

1. **Phase A — Instrumentation.** State logger + event hooks in the target engine; verify field
   coverage against R2's anticipated needs (doors, chests, NPCs, quest flags all present).
2. **Phase B — Pipeline.** Shard builder profile for the target; sync verification; chunking
   choice recorded (long chunks like M2 if the runtime work will need them).
3. **Phase C — Validation tooling.** The three checks from the goal prompt: (1) load random
   clips through the dataset API; (2) replay a state timeline and diff against a re-run
   (determinism check from R0's probe, now automated); (3) a debug view overlaying object IDs +
   events on captured frames (marimo browser extension).
4. **Phase D — Corpus.** Capture the slice thoroughly: all loops, repeated with variation,
   deliberate leave-and-return runs, failure cases (death), menus. Reserve named replay traces
   (regression split, as in M2 §1.5). Asset manifest completed.

## 3. Non-goals

- No schema normalization (R2 — sidecar stays raw/engine-shaped here).
- No mechanics inference (R3), no training (R4+).
- No capture of content outside the R0 slice.

## 4. Tests & verification

- Shard round-trip and frame/JSONL/state alignment tests (reuse M2's suites).
- State-logger coverage test: every field in the R2 wishlist present-or-documented-absent.
- Deterministic replay test automated in CI for the pipeline repo.
- Asset manifest validation: every extracted file has a manifest row with a license.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Engine state incomplete (hidden logic not logged) | Coverage report vs the R2 wishlist; gaps documented now — they become R3 "rule recovery" work, not surprises |
| Nondeterminism breaks replay validation | Quantify it (which subsystems drift); record RNG seeds; R3 will need this catalog anyway |
| Asset rights narrower than assumed | Manifest gates all downstream use; ambiguous assets marked `training_only` or excluded |
| Divergence from M2's format | Shared shard-builder code path; a format test asserting mira-dataset loadability |

## 6. Effort & definition of done

A (~1 week) → B (~½ week) → C (~1 week) → D (~1–2 weeks of capture).

**Done when:** the full slice corpus loads via the mira dataset API and the overlay debug view;
state timelines replay deterministically (or drift is quantified and documented); event labels
verified; asset manifest complete with licenses; replay/regression traces reserved.
