---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: "Awaiting `/gsd:plan-phase 0`"
last_updated: "2026-05-19T23:43:35.445Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: Vision — Cycling Form & Performance Analyzer

**Last updated:** 2026-05-20

## Project Reference

- **Core value:** Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on
- **Mode:** mvp
- **Granularity:** coarse
- **Phases:** 7 (Phase 0 — Phase 6)
- **JD signals (4):** CS/Engineering, computer vision / pose estimation, GCP-based ML workloads, sport/performance telemetry
- **Current focus:** Pre-Phase-0 — roadmap is approved; awaiting plan creation for Phase 0

## Current Position

- **Phase:** Phase 0 — Bootstrap & Cost Guardrails (not started)
- **Plan:** None
- **Status:** Awaiting `/gsd:plan-phase 0`
- **Progress:** `[                    ]` 0 / 7 phases complete

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

- Phases planned: 0
- Phases shipped: 0
- Average plans per phase: TBD
- Average node-repair invocations per phase: TBD (budget = 2)

## Accumulated Context

### Decisions Logged

| ID | Decision | Source | Rationale |
|----|----------|--------|-----------|
| ADR-1 | Cloud Run Jobs (not Vertex AI Endpoint, not Cloud Run Service) for pose inference | `research/ARCHITECTURE.md` | Vertex AI Endpoint ~$160/mo idle busts $20/mo budget; Cloud Run Service 60-min timeout cliff is dangerous for 90-min rides; Cloud Run Jobs scale-to-zero, 7-day task timeout |
| ADR-2 | Time alignment as a BigQuery SQL view, not in compute jobs | `research/ARCHITECTURE.md` | Per-ride scalar offset stored in `rides` metadata; `fused_timeline` view applies offset on JOIN; alignment failures are instantly debuggable; reprocessing pose/FIT doesn't require re-running alignment |
| ADR-3 | Pose inference always runs in cloud (not local-only) for the shipped pipeline | `research/ARCHITECTURE.md` | JD bullet is "GCP-based ML workloads"; pose running only on a laptop doesn't satisfy it; same container runs both places |
| GRAN | Coarse granularity (6-7 phases) | `config.json` | MVP mode; favor end-to-end thin slice over deep specialization (per PROJECT.md timeline constraint of 4-8 weekends) |

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

### Next Session

Run `/gsd:plan-phase 0` to decompose Phase 0 (Bootstrap & Cost Guardrails) into executable plans.

Phase 0 is non-negotiable and must complete before any GCP deploy. The load-bearing acceptance criterion is the billing kill switch deployed AND tested.

---
*State initialized: 2026-05-20 after roadmap approval*
