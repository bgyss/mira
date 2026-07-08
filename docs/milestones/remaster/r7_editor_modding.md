# R7 — Create the Editor and Modding Surface

**Objective:** expose the remaster package as something designers can inspect and edit — entity
browser, mechanics editor, trace viewer, modding API, and safety checks — prioritizing
**verifiable edits over broad creative freedom**.

## 0. Context & prerequisites

- **Depends on:** R2 (schema), R3 (rule files), R6 (adapter toggles); R4/R5 for preview
  rendering. A read-only trace viewer can start during R1/R2 (and partially exists as the R1
  overlay debug view) — but editing features wait until the mechanics graph and renderer are
  stable enough to be worth editing.
- Technology: extend the marimo-based tooling for the viewer where practical; the editor proper
  is a local web app (the R8 runtime bundle is its data source), kept out of `src/mira`.

## 1. Components

### 1.1 Entity browser

Table/inspector over the R2 entity database: object IDs, class, pose, affordances, persistent
state, linked assets (via the R1 manifest), and "appears in traces" cross-references. Read-only
first; then guarded edits (pose nudges, state defaults, item stats).

### 1.2 Mechanics editor

Edits R3's declarative rule files: view the graph (nodes, reads/writes, priorities), edit
parameters, add/disable rules — with validation on save (schema check, read/write declarations,
cycle/priority conflicts) and a one-click "run affected trace tests" button (test selection: any
replay trace exercising the edited rule's reads/writes).

### 1.3 Trace viewer

Timeline-scrubbed side-by-side: original frame | remastered frame | schema state | events | rule
effects fired that frame. This is the debugging heart of the whole program — invest accordingly.

### 1.4 Modding API

Programmatic layer (Python) the UI itself uses — same operations scriptable: add/edit objects,
encounters, item stats, dialogue branches, simple quest flags. Every mutation goes through the
schema validators and emits an edit log entry (undo + provenance).

### 1.5 Safety checks

On-save analyses: puzzle solvability (the slice's quest remains completable — graph reachability
over quest transitions), unreachable-object detection (referenced but unplaceable/inaccessible),
invalid quest-graph transitions, and automatic replay-test selection for the edited surface.

## 2. Phased execution

1. **Phase A — Trace viewer.** §1.3 over the existing corpus; ship early, use it while building
   the rest.
2. **Phase B — Entity browser + modding API (read → write).** API first, UI on top; edit log +
   undo.
3. **Phase C — Mechanics editor.** §1.2 with validation + test-runner integration.
4. **Phase D — Safety checks + acceptance demo.** §1.5; the goal-prompt demo: a user inspects
   entities, edits one encounter/interaction, runs affected trace tests, previews original vs
   remastered playback.

## 3. Non-goals

- No general content-creation suite (no mesh editing, level design, or dialogue authoring beyond
  branch edits); no multi-user collaboration; no cloud anything.
- No adapter *training* from the editor (R6 owns training; the editor toggles).

## 4. Tests & verification

- Modding API: unit tests per mutation type; validator rejection tests; edit-log round-trip/undo.
- Safety checks: fixture worlds with known-broken states (unsolvable quest, orphaned object) —
  each must be caught.
- Trace-test selection: edited rule ⇒ selected tests provably cover its reads/writes.
- UI smoke tests (headless) for each component against a fixture package.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Editor scope explodes | Component order fixed A→D; each phase ships usable alone; "verifiable edits" is the acceptance bar for any feature request |
| Solvability checking is undecidable in general | Scope to the slice's quest graph (finite flags) — plain reachability; document the limits |
| Edits corrupt packages | All mutations via the validated API + edit log; packages are versioned snapshots (R8 manifest) |
| Preview rendering too slow for interactive editing | Preview uses cached/replayed renders; live re-render is async, not blocking |

## 6. Effort & definition of done

A (~2 weeks) → B (~2 weeks) → C (~2 weeks) → D (~1–2 weeks).

**Done when:** the Phase D demo runs end-to-end for a non-author user; safety checks catch the
fixture regressions; every UI mutation is available via the scriptable API with tests; the trace
viewer is in daily use by the team.
