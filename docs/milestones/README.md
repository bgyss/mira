# Milestone Execution Plans

Expanded, execution-ready plans for the two milestone tracks:

- `../rpg_expansion_milestones.md` — MIRA → open-world RPG world models (M0–M8)
- `../game_remaster_milestones.md` — old-game remaster factory (R0–R10)

Each plan follows the structure proven by `../m0_refactor_plan.md`: **Objective**, **Context &
prerequisites**, **Design**, **Phased execution** (each phase lands green and is independently
revertable), **Tests & verification**, **Non-goals**, **Risks & mitigations**, and a
**Definition of done**. Plans are written so an agent/engineer can pick one up cold.

## RPG track (`rpg/`)

| Milestone | Plan | Depends on |
|---|---|---|
| M0 — Decouple from Rocket League | `../m0_refactor_plan.md` (pre-existing) | — |
| M1 — Generalized action space | `rpg/m1_action_space.md` | M0 |
| M2 — RPG capture & ingestion | `rpg/m2_capture_pipeline.md` | M0, M1 (schema) |
| M3 — General-purpose codec | `rpg/m3_general_codec.md` | M2 (data) |
| M4 — First RPG world model | `rpg/m4_first_rpg_world_model.md` | M1–M3 |
| M5 — Long-horizon memory | `rpg/m5_long_horizon_memory.md` | M4 |
| M6 — Discrete state & mechanics boundary | `rpg/m6_discrete_state.md` | M4 |
| M7 — Multi-game conditioning & transfer | `rpg/m7_multi_game.md` | M5, M6 |
| M8 — Real-time interactive play | `rpg/m8_realtime_play.md` | M5–M7 |

## Remaster track (`remaster/`)

| Milestone | Plan | Depends on |
|---|---|---|
| R0 — Target selection | `remaster/r0_target_selection.md` | — |
| R1 — Trace & asset extraction | `remaster/r1_trace_extraction.md` | R0 |
| R2 — Remaster state schema | `remaster/r2_state_schema.md` | R1 |
| R3 — Mechanics graph | `remaster/r3_mechanics_graph.md` | R2 |
| R4 — Neural remaster renderer | `remaster/r4_neural_renderer.md` | R2 |
| R5 — State-conditioned world model | `remaster/r5_state_conditioned_wm.md` | R3, R4 |
| R6 — Mechanic & style adapters | `remaster/r6_adapters.md` | R5 |
| R7 — Editor & modding surface | `remaster/r7_editor_modding.md` | R3, R6 |
| R8 — Playable runtime export | `remaster/r8_runtime_export.md` | R5–R7 |
| R9 — Validation suite | `remaster/r9_validation.md` | R8 |
| R10 — Pipeline scaling | `remaster/r10_pipeline_scaling.md` | R9 |

The two tracks share infrastructure deliberately: R1/R2 reuse M2's capture format, R5 reuses the
M6 state-conditioning path, and R4/R5 reuse the M3 codec. Where a remaster milestone depends on an
RPG-track capability, the plan says so explicitly.
