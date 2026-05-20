---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: "Phase 0 in progress (2/7 plans complete)"
last_updated: "2026-05-20T12:59:04.139Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 7
  completed_plans: 2
  percent: 29
---

# Project State: Vision — Cycling Form & Performance Analyzer

**Last updated:** 2026-05-20

## Project Reference

- **Core value:** Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on
- **Mode:** mvp
- **Granularity:** coarse
- **Phases:** 7 (Phase 0 — Phase 6)
- **JD signals (4):** CS/Engineering, computer vision / pose estimation, GCP-based ML workloads, sport/performance telemetry
- **Current focus:** Phase 0 — Bootstrap & Cost Guardrails (in progress)

## Current Position

- **Phase:** Phase 0 — Bootstrap & Cost Guardrails (in progress)
- **Plan:** Next: 00-03 (after 00-02 repo hygiene shipped 2026-05-20)
- **Status:** Phase 0 in progress (2/7 plans complete)
- **Progress:** [███░░░░░░░] 29% (2/7 plans)

### Phase Pipeline

- [ ] Phase 0: Bootstrap & Cost Guardrails
- [ ] Phase 1: Local Thin Slice (No GCP)
- [ ] Phase 2: Containerize Each Stage
- [ ] Phase 3: GCP Storage + Manual Job Invocation
- [ ] Phase 4: Orchestration (Workflows + Eventarc)
- [ ] Phase 5: Viewer (Streamlit) + Deployment Polish
- [ ] Phase 6: Portfolio Polish & Narrative

## Requirements Coverage

- v1 requirements: 53 total
- Mapped to phases: 53
- Unmapped: 0
- See `REQUIREMENTS.md` for the authoritative traceability table

## Performance Metrics

- Phases planned: 1 (Phase 0)
- Phases shipped: 0
- Plans shipped: 2 (00-01 Python toolchain ~2m; 00-02 repo hygiene ~4m)
- Average plans per phase: TBD
- Average node-repair invocations per phase: TBD (budget = 2)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 00-bootstrap-cost-guardrails | 01 | 2m | 1 | 7 |
| 00-bootstrap-cost-guardrails | 02 | 4m | 1 | 3 |

## Accumulated Context

### Decisions Logged

| ID | Decision | Source | Rationale |
|----|----------|--------|-----------|
| ADR-1 | Cloud Run Jobs (not Vertex AI Endpoint, not Cloud Run Service) for pose inference | `research/ARCHITECTURE.md` | Vertex AI Endpoint ~$160/mo idle busts $20/mo budget; Cloud Run Service 60-min timeout cliff is dangerous for 90-min rides; Cloud Run Jobs scale-to-zero, 7-day task timeout |
| ADR-2 | Time alignment as a BigQuery SQL view, not in compute jobs | `research/ARCHITECTURE.md` | Per-ride scalar offset stored in `rides` metadata; `fused_timeline` view applies offset on JOIN; alignment failures are instantly debuggable; reprocessing pose/FIT doesn't require re-running alignment |
| ADR-3 | Pose inference always runs in cloud (not local-only) for the shipped pipeline | `research/ARCHITECTURE.md` | JD bullet is "GCP-based ML workloads"; pose running only on a laptop doesn't satisfy it; same container runs both places |
| GRAN | Coarse granularity (6-7 phases) | `config.json` | MVP mode; favor end-to-end thin slice over deep specialization (per PROJECT.md timeline constraint of 4-8 weekends) |
| TC-1 | Hatchling build backend + PEP 735 `[dependency-groups]` for dev tools | `00-01-SUMMARY.md` | First-class uv support; keeps dev tools out of the user-facing optional-group namespace; pyproject.toml shape is now the template every later phase preserves |
| TC-2 | Optional-dependency groups (pose/telemetry/data/gcp/weather/viewer/cli + meta `all`) instead of a flat dependency list | `00-01-SUMMARY.md` | Phase 0 CI stays fast (no MediaPipe wheel install); Phase 2 containers install only the groups each stage needs |
| TC-3 | `requires-python = ">=3.12,<3.13"` (with upper bound) | `00-01-SUMMARY.md` | MediaPipe has no 3.13 wheels per STACK.md; upper bound is load-bearing and must be preserved across all later phases until MediaPipe ships 3.13 wheels |
| HYG-1 | Blanket `*.json` in `.gitignore` (D-14) with documented intent to re-allow via `!path/*.json` in later phases | `00-02-SUMMARY.md` | Defense-in-depth across all subdirectories blocks a stray service-account JSON dropped anywhere in the tree, at the cost of one negation per legitimately-committed JSON family (e.g. `!infra/bigquery/schemas/*.json` in Phase 3) |
| HYG-2 | Public-repo secret-hygiene is a two-layer contract: `.gitignore` enforcement + `CONTRIBUTING.md` §Never-commit-secrets documentation (D-27) | `00-02-SUMMARY.md` | Both files must be updated in sync whenever a new secret-shaped artifact category emerges; documentation without enforcement is theatre, enforcement without documentation invites footguns |
| HYG-3 | `!.env.example` negation pattern is the canonical "show the template, hide the real env" idiom | `00-02-SUMMARY.md` | Applies repo-wide (root and subdirectories); verified working for `scripts/bootstrap-gcp.env.example` (D-03) and any future `*.env.example` template |

### TODOs

- [ ] Acquire ≥3 fixture rides (real or synthetic) for Phase 1 — flagged early in `research/SUMMARY.md` "Gaps to Address"
- [ ] Acquire ≥6 edge-case FIT fixtures for Phase 1 (paused ride, dual-sensor, power dropout, smart-recording variable rate, indoor, outdoor) — per Pitfall #9
- [ ] Decide on manual vs auto alignment for v1 during Phase 1 synthetic-offset test (per SUMMARY.md "Gaps to Address")
- [ ] Calibrate bilateral-metric visibility threshold against first 1-3 real rides in Phase 1

### Blockers

None.

### Research Flags (carry into plan-phase)

- **Phase 1:** time-alignment signal processing (linear-fit drift correction, residual thresholds, synthetic-test patterns) + MediaPipe Tasks API specifics — run `/gsd-research-phase 1` before planning
- **Phase 4:** Eventarc + Workflows + Cloud Run Jobs coupling — run `/gsd-research-phase 4` before planning

## Session Continuity

### Recent Sessions

| Date | Activity | Outcome |
|------|----------|---------|
| 2026-05-20 | Project initialization | PROJECT.md + REQUIREMENTS.md + research dossier (STACK / ARCHITECTURE / PITFALLS / SUMMARY) created |
| 2026-05-20 | Roadmap creation | ROADMAP.md + STATE.md written; 53/53 v1 requirements mapped to 7 phases (Phase 0 — Phase 6) |
| 2026-05-20 | Phase 0 planning | 7 plans decomposed under `.planning/phases/00-bootstrap-cost-guardrails/` |
| 2026-05-20 | Phase 0 Plan 01 executed | Python 3.12 toolchain shipped (`pyproject.toml` + `uv.lock` + `lib/vision/` + smoke tests); all four CI gates green; commit `9695448` |
| 2026-05-20 | Phase 0 Plan 02 executed | Repo hygiene shipped: full BOOT-07 `.gitignore` (credentials, raw FIT/TCX/GPX, large fixture artifacts, Python/caches), `CONTRIBUTING.md` with load-bearing `Never commit secrets` H2 (D-27), `NOTICE` stub signposted for plan 00-03; all 6 `git check-ignore` behavior tests pass; commit `523111a` |

### Next Session

Execute Phase 0 Plan 03 next (vendor Cyclenerd kill-switch into `infra/kill-switch/`; populate `NOTICE` with upstream credit). Phase 0 is non-negotiable and must complete before any GCP deploy. The load-bearing acceptance criterion is the billing kill switch deployed AND tested.

---
*State initialized: 2026-05-20 after roadmap approval*
