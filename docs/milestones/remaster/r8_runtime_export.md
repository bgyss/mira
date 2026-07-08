# R8 — Export a Lightweight Playable Runtime

**Objective:** package the remaster as a portable, versioned runtime bundle — schemas, mechanics
graph, entity database, legal assets, renderer/world-model checkpoints, adapters, replay tests,
manifest — with a working play loop, save/load, deterministic replay, and a latency profile.
"Packability" is the product claim; this milestone proves it.

## 0. Context & prerequisites

- **Depends on:** R3 (mechanics), R4/R5 (neural stack), R6 (adapters), R2 (schemas). Shares the
  real-time architecture with the RPG track's M8 (hybrid loop, few-step sampling, save/replay
  design) — reuse its inference server and distillation work where the checkpoints allow.

## 1. Design

### 1.1 Runtime loop

`input → mechanics/state (authoritative, CPU) → conditioning assembly → world model / renderer
(GPU) → frame (+ audio + UI)`. Same shape as M8 §1.1; the remaster additions are the entity
database in the loop (object tokens) and adapter stacks applied at load. UI/HUD may be composited
symbolically (the mechanics layer knows the values) — decide per the M6/R5 menu findings and
record it.

### 1.2 Bundle format (the `remaster_project/` layout, made concrete)

```text
bundle/
  manifest.json          # versions of everything + dependency constraints + hashes
  state_schema/          # R2 schema (versioned)
  mechanics_graph/       # R3 rule files
  entity_database/       # R2 entities for the slice
  quest_graph/           # slice quest transitions
  assets/                # manifest-cleared legal assets only
  checkpoints/           # codec, world model, renderer (+ distilled samplers)
  adapters/              # R6 adapter payloads
  test_replays/          # regression traces + expected outcomes
```

Manifest pins schema versions, checkpoint hashes, adapter compat, and minimum
hardware/dependency constraints. A bundle validator checks integrity + license flags (no
`training_only` assets escape into a bundle).

### 1.3 Save/load & replay

Save = explicit schema state + adapter selection + RNG seeds + model context; replay runner
re-executes original **and modded** traces against a bundle and diffs outcomes — this is R9's
execution vehicle. Deterministic replay is guaranteed for the explicit-state path; neural frames
are deterministic per fixed seed/checkpoint/hardware and otherwise compared by metric, not bits.

### 1.4 Performance profile

Per-stage latency breakdown (mechanics / conditioning / denoise / decode / present) via the
`bench_wm_speed.py` methodology; a minimum-hardware target statement; a written assessment of
what a browser or low-end-desktop demo would require (quantization, resolution, step count) —
assessment only, not implementation.

## 2. Phased execution

1. **Phase A — Bundle format + validator.** Manifest schema, packer from the working tree,
   loader that boots a runtime purely from a bundle on a clean machine.
2. **Phase B — Runtime loop.** Interactive loop from bundle contents; reuse/port the M8 server
   if available; play the slice's loops live.
3. **Phase C — Save/load + replay runner.** §1.3 with determinism tests; run the full
   `test_replays/` set from the bundle.
4. **Phase D — Profile + hardening.** Latency report, minimum-hardware doc, browser/low-end
   assessment; a second machine reproduces everything from the bundle alone.

## 3. Non-goals

- No browser build, no installer/distribution polish, no audio synthesis beyond passing through
  extracted audio assets; no new model training (distilled samplers come from M8's work or a
  minimal port of it).

## 4. Tests & verification

- Bundle validator tests (corrupt/hash-mismatch/license-flag fixtures rejected).
- Clean-machine boot test (CI job in a fresh container).
- Deterministic replay tests for the explicit-state path; metric-based comparison for frames.
- Save/load round-trip: quit/reload mid-quest, state identical.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Hidden working-tree dependencies (bundle isn't actually portable) | Clean-machine CI boot test from Phase A onward |
| Checkpoint size makes bundles unwieldy | Quantized/distilled checkpoints in the bundle; full ones referenced by hash for reproducibility |
| Replay nondeterminism from GPU/kernel variance | Explicit-state determinism is the guarantee; frame comparison is metric-based by design |
| License leakage into shipped bundles | Validator enforces manifest flags; R1's manifest is the single authority |

## 6. Effort & definition of done

A (~2 weeks) → B (~2–3 weeks) → C (~1–2 weeks) → D (~1 week).

**Done when:** a bundle built by the packer boots and plays on a clean machine; save/load and
deterministic explicit-state replay tested; original + modded replays run from `test_replays/`;
latency breakdown and minimum-hardware target published; browser/low-end requirements documented.
