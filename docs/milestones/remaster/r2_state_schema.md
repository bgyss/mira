# R2 — Define the Remaster State Schema

**Objective:** convert R1's raw, engine-shaped traces into a versioned, object-centric schema —
the stable handles that mechanics (R3), tests (R9), editing tools (R7), and neural conditioning
(R4/R5) all build on. "Door stayed open" and "NPC remembers the quest" are schema problems before
they are model problems.

## 0. Context & prerequisites

- **Depends on:** R1 corpus + sidecars.
- Precedents to follow: pydantic models with `extra="forbid"` + versioning + the
  `REMOVED_CONFIG_FIELDS`-style migration discipline used across mira; schema-v2 opaque payload
  becomes typed here for the remaster sidecar (the mira core still treats it as opaque —
  the typed schema lives in the remaster package).

## 1. Schema design (new package, e.g. `remaster/state_schema/`)

### 1.1 `GameObject`

`{object_id (stable, engine-derived), class, pose, bounds/collision_token, animation_state,
affordances (openable/lootable/talkable/...), visibility, material/style_token,
persistent_state (typed per class: door open/locked, chest looted, NPC disposition...)}`

Stable-ID policy is the heart of this milestone: engine IDs where the engine has them; otherwise
a deterministic derivation (spawn-point + class + counter) documented and tested — the same
object must resolve to the same ID across clips, sessions, and save/loads.

### 1.2 Player & camera

Player: pose, velocity, input ref, equipment, health/stamina/mana, lock-on target (object_id),
current mode (gameplay/menu/dialogue), save/load metadata. Camera: pose, FoV, mode, target.

### 1.3 Quest / dialogue / inventory (scoped to the R0 slice)

Quest: flag set + typed transitions actually used by the slice's one quest. Dialogue: node id +
branch taken. Inventory: item ids (stable, from the asset manifest), counts, equip slots. Do not
design generality the slice doesn't exercise.

### 1.4 Frames, events, versioning

- `StateFrame`: timestamp + player + camera + object deltas (full keyframes every N frames,
  deltas between — traces are long).
- Events reference `object_id`s (pickup → item + actor; door change → door id).
- `schema_version` on every record; migration rules: **new fields additive with defaults; removed
  fields tolerated only at their old no-op value** (the repo-wide discipline); old traces must
  remain loadable forever.

## 2. Phased execution

1. **Phase A — Schema + normalizer.** Pydantic models; a normalizer from R1 sidecars →
   typed records; run over the full corpus, triaging every field that fails to map
   (fix schema or document as unavailable).
2. **Phase B — Stable-ID proof.** The milestone's core test: track named objects (specific door,
   chest, NPC) across (a) leaving/re-entering camera view, (b) area leave/return, (c) state
   changes, (d) save/load; assert one ID throughout. Build the ID-audit report tool.
3. **Phase C — Round-trip & versioning tests.** Trace → schema → serialized → schema equality;
   a frozen v1 fixture corpus checked into tests so future migrations are regression-tested;
   write a v1→v2 dummy migration to prove the mechanism.
4. **Phase D — Integration.** Overlay debug view (R1 Phase C) upgraded to show schema records;
   dataset sidecar readers expose typed records to downstream milestones.

## 3. Non-goals

- No rules/behavior (R3); no conditioning encoders (R4/R5); no editing UI (R7).
- No universal cross-game schema — this is the slice's schema; R10 generalizes.

## 4. Tests & verification

- Round-trip tests per record type; property tests on delta/keyframe reconstruction.
- Stable-ID tests per §Phase B scenario, using named objects from real traces.
- Migration tests against the frozen fixture corpus.
- Normalizer coverage report: % of raw fields mapped, with an explicit unmapped list.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Engine IDs unstable across save/load | Deterministic ID derivation fallback, tested in Phase B(d) specifically |
| Over-modeling (schema astronautics) | Every field must be exercised by the R1 corpus or a named R3/R9 consumer |
| Delta encoding bugs corrupt long traces | Keyframe interval + reconstruction property tests; checksum per chunk |
| Schema churn destabilizes R3/R4 in flight | Version gate: R3 starts only after v1 freeze; changes go through migrations |

## 6. Effort & definition of done

A (~1 week) → B (~1 week) → C (~½ week) → D (~½ week).

**Done when:** the full R1 corpus normalizes into schema v1 with a published coverage report;
stable-ID tests pass for all four scenarios; round-trip + migration tests green; v1 frozen and
consumed by the overlay viewer; R3 can enumerate reads/writes purely in schema terms.
