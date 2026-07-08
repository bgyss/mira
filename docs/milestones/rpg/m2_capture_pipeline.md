# M2 — RPG Data Capture & Ingestion Pipeline

**Objective:** a repeatable capture harness that turns real PC action-RPG gameplay into
MIRA-format shards: fixed-fps video + per-frame gamepad JSONL + metadata + optional structured
state, chunked for long-context training, with automatic segment annotation and a reserved
replay/regression split. Target: **100+ hours** for the first game before M4 training.

## 0. Context & prerequisites

- **Depends on:** M0 (schema v2 / `GameSpec`), M1 (axes JSONL format & `AxisSpec`).
- Existing contracts to reuse, not reinvent:
  - WebDataset sample = one *(match, chunk)*: `p{i}.mp4` + `p{i}.jsonl` + `meta.json`, with
    `index.json` per `src/mira/data/schema.py` (`MatchEntry` random access). RPG capture is
    `n_players=1` — one perspective per "match" (= session).
  - Clips never span chunk boundaries (`dataset.py` clip/chunk contract).
  - Events on a shared match clock (`events.py` `Event`/anchor pattern — generic after M0).
  - Marimo browser (`pixi run explore`) as the validation surface.
- **Game choice:** Elden Ring on PC is the pragmatic first target (native input capture, no
  emulation). BotW/TotK require emulation with unresolved ToS questions — **blocked on the legal
  review in the cross-cutting workstream; do not invest capture engineering there until cleared.**

## 1. Design

### 1.1 Capture tool (new top-level `capture/` package or repo)

Keep it out of `src/mira` (it has OS-level deps — screen capture, controller hooks); it only needs
to *emit* the mira format.

- **Video:** fixed 30fps, hardware-encoded (NVENC) H.264/HEVC readable by torchcodec 0.7.0/FFmpeg
  7. Native capture resolution recorded in metadata; downscaling happens at training time.
  Frame timestamps recorded so drops are detected, not silently absorbed.
- **Input:** per-frame gamepad state via a controller hook (e.g. SDL/XInput polling at ≥60Hz,
  bucketed to frames): `keys` (buttons, M1 multi-hot names) + `axes` (M1 `AxisSpec` names,
  normalized to [-1, 1] post-deadzone). One JSONL line per video frame — the alignment invariant
  the loader relies on.
- **Sync:** a startup clap-pattern (scripted input burst + on-screen response) recorded at session
  start to measure input→frame latency; store the measured offset in `meta.json` and shift the
  JSONL at shard-build time.
- **Session metadata:** game id/version, capture settings, controller model, deadzones,
  resolution/fps, in-game settings (camera sensitivity!, HUD scale), session UUID.

### 1.2 Optional state taps (best effort, layered)

Store as a per-frame sidecar `state.jsonl` (schema-v2 per-game payload; opaque mapping per M0),
never required by the core pipeline:

- Tier 1 (cheap, always on): HUD extraction via OCR/template matching offline — HP/FP/stamina
  bars, runes counter, region name toasts. Offline pass, not in the capture hot loop.
- Tier 2 (per-game): mod/debug APIs or memory scanning (e.g. Cheat Engine tables for
  camera/player pose, target lock state) — **single-player offline only; never with anti-cheat /
  online enabled**. Document exactly what is read and why.
- Tier 3: save-file checkpoints snapshotted at session boundaries and death/respawn events.

### 1.3 Chunking policy

- **30s chunks @ 30fps = 900 frames per chunk** (vs RL's 4s/80). Rationale: M5's long-context and
  revisit work needs long contiguous windows; intra-chunk clip sampling keeps training flexible.
  Make chunk length a shard-build parameter; record it in `index.json`.
- Shard builder is a separate offline step: raw session → validated, resynced, chunked shards.
  Raw sessions are the archival source of truth (provenance principle).

### 1.4 Segment annotation pass (offline, feeds M6)

Automatic detectors over the finished video, emitting `Event`s on the match clock:

- menu/inventory/map open-close (template/HUD-layout classifier),
- loading screens (near-black + logo heuristics),
- cutscenes (letterboxing / input-ignored spans),
- death ("YOU DIED" template — high precision), respawn, fast-travel.

Each detector reports confidence; low-confidence spans go to a lightweight review queue in the
marimo browser. Annotations live in `meta.json` events, versioned so re-running an improved
detector regenerates them without touching video.

### 1.5 Replay/regression split

Reserve *named* trace sets, excluded from training shards by index-level tags:

- golden-path segments (tutorial → first boss route),
- combat encounters (specific enemies, lock-on sequences),
- door/chest/interaction loops, and **area revisit loops** (deliberately walk A→B→A) — captured
  intentionally, since M5's revisit metric needs them.

### 1.6 Config

`configs/dataset/elden_ring.yaml` implementing the M0 dataset-config contract: `game: elden_ring`,
`n_players: 1`, `source_fps: 30`, `target_fps` (decided with M3), `actions` sub-config listing the
gamepad button vocab + axes.

## 2. Phased execution

### Phase A — Capture prototype & format freeze

1. Record 1 hour of Elden Ring with video+input; measure drop rate, sync offset stability.
2. Freeze the JSONL/meta format against M1's parser; write the shard builder for one session.
3. Load resulting shards through the (post-M0) generic dataset API; view clips in marimo with the
   input timeline overlaid. **Gate: a human confirms input↔video alignment visually** (button
   press ↔ animation onset within 1–2 frames).

### Phase B — Annotation pass & state taps

1. Implement Tier-1 HUD extraction + segment detectors; evaluate detector precision/recall on a
   hand-labeled 30-minute set (target: ≥95% precision on death/loading, ≥90% on menus).
2. Prototype one Tier-2 tap (camera/player pose) if a safe route exists; otherwise document why
   not and rely on Tier 1.

### Phase C — Scale capture

1. Capture playbook doc: session checklist, content coverage matrix (biomes, day/night, combat,
   towns, menus), revisit-loop instructions per §1.5.
2. Run capture to 100+ hours; nightly shard builds + an automated QA report (drop rate, sync
   drift, annotation coverage, per-region content histogram).

### Phase D — Regression split & handoff

1. Tag replay traces in `index.json`; loader-level exclusion tested.
2. Dataset card (mirroring `docs/dataset_card.md`) with provenance, license notes, coverage stats.

## 3. Non-goals

- No emulated-console capture (blocked on legal review).
- No codec/world-model training (M3/M4); no state *conditioning* (M6) — M2 only records state.
- No multi-game loader (M7).

## 4. Tests & verification

- Shard-builder unit tests: frame/JSONL count agreement, sync-offset application, chunk boundary
  exactness, `index.json` validation against schema v2.
- Round-trip test: synthetic session (generated frames + inputs) → shards → loader → assert
  actions/axes tensors match the generated ground truth.
- Annotation detectors: fixture screenshots per class; precision/recall regression thresholds.
- End-to-end: `pixi run explore` renders RPG clips with event overlays.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Anti-cheat / ToS exposure from memory reads | Offline-only, documented reads, legal signoff before Tier 2; Tier 1 (pixels-only) is always available |
| Input/video desync drifts over long sessions | Per-session sync measurement + periodic re-sync markers; QA report tracks drift |
| Frame drops corrupt the 1-line-per-frame invariant | Timestamped capture; builder inserts explicit blank lines for dropped frames and flags sessions above a drop threshold |
| 100h capture stalls the schedule | Phase A/B unblock M3/M4 with partial data (~20h is enough for first codec/WM experiments); scale in parallel |
| HUD OCR fragile across resolutions/HUD scales | Fix capture resolution + HUD settings in the playbook; detectors keyed to that profile |

## 6. Sequencing & effort

A (~1 week incl. tooling) → B (~1 week) → C (background, weeks, parallel with M3) → D (~2 days).

**Definition of done:** ≥100h Elden Ring shards loadable via the generic dataset API and browsable
in marimo; input↔video alignment verified; segment annotations with measured precision; named
replay split excluded from training; `configs/dataset/elden_ring.yaml` merged; dataset card
written; capture playbook reproducible by someone else.
