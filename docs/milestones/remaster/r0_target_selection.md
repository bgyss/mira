# R0 — Choose a Legal, Instrumentable Prototype Game

**Objective:** select the first remaster target and write the target selection memo that
constrains every later milestone: what we can capture, what state we can observe, which assets we
can legally use and redistribute, and the exact gameplay loops to remaster.

## 0. Context

The project succeeds or fails on **observability and rights**. A famous closed RPG blocks capture
automation, asset reuse, mod APIs, and demo sharing. This milestone is research + a decision —
no code beyond throwaway feasibility probes.

## 1. Candidate slate (evaluate ≥3; suggested starting slate)

1. **OpenMW + Morrowind assets** — open-source engine (full state access, deterministic replay
   feasible, scriptable), but Bethesda-owned assets constrain redistribution; a
   free asset replacement project (e.g. Project Atlas-style or OpenMW example suite) could unlock
   sharing.
2. **An open-source 3D game** with RPG-ish loops (e.g. a Godot/Unity open demo, Veloren, or a
   community Zelda-like) — cleanest rights, engine instrumentation trivial, but content depth and
   "remaster payoff" vary.
3. **A homebrew slice built for the project** — a small Godot/Unity test map (one town, one
   dungeon, one combat loop) instrumented from day one; maximal observability, total rights, but
   weakest "archaeology" story and we must build the game first.
4. (Stretch comparison only) an emulated retro RPG — strong story, but capture/asset/ToS risk;
   include in the memo to document *why not first*.

## 2. Evaluation rubric (score each candidate; the memo shows the table)

| Criterion | What to verify concretely |
|---|---|
| Legal status | License of engine, assets, scripts; ToS on automation/capture; redistribution rights for a public demo |
| Instrumentation access | Can we log per-frame state (poses, health, inventory, quest flags, object IDs) from source, mod API, or debug hooks? |
| Asset availability | Meshes/textures/audio extractable in documented formats, with rights to transform them |
| Replay determinism | Fixed seed + recorded input ⇒ identical run? (Feasibility probe: record/replay 5 min and diff state) |
| Demo shareability | Can the finished slice be shown publicly, including derived assets? |
| Remaster payoff | Would a visual upgrade be *visibly* compelling? |
| Scope fit | Contains one area + traversal + interaction + combat + menu loop of tractable size |

Feasibility probes are timeboxed (≤1 day each): a state-logging spike and a record/replay
determinism spike per shortlisted candidate.

## 3. Deliverables

1. **Target selection memo** (`docs/remaster/target_selection.md`): scored table, probes'
   results, the recommendation, and the binding constraints for R1–R10 (what we may capture,
   store, train on, and ship).
2. **Scope cut:** the exact slice — one area, one traversal loop, one interaction loop
   (door/chest/pickup), one combat loop, one menu loop — named concretely (specific map, enemies,
   items).
3. **Success criteria for the slice** (acceptance targets referenced by R9): trace replay passes,
   object persistence across leave/return, visual upgrade temporal consistency, one editable
   mechanic demonstrated, runtime export runs on a target machine.

## 4. Non-goals

- No pipeline code, no capture tooling (R1), no schema design (R2).
- No commitment to famous closed titles regardless of enthusiasm — the memo may list them as
  "later, if X" only.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Rights ambiguity discovered late | Legal review of the memo is a phase gate before R1 spends effort |
| Chosen game's state access worse than probed | Determinism + state-logging probes are mandatory before signoff |
| Scope creep in the slice definition | Slice named as concrete content; anything else needs a memo amendment |
| Homebrew option quietly becomes "build a whole game" | Timebox: if the test map exceeds ~2 weeks of build effort, it fails Scope fit |

## 6. Effort & definition of done

~1–2 weeks. **Done when:** memo reviewed and signed off (including legal review of capture/asset/
redistribution positions); slice and success criteria written; probes' artifacts archived; R1 can
start with no open rights questions.
