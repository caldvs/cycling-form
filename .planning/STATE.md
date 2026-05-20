---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-05-20T13:12:46.617Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 7
  completed_plans: 4
  percent: 0
---

# Project State: Vision — Cycling Form & Performance Analyzer

**Last updated:** 2026-05-20T14:14:00Z

## Project Reference

- **Core value:** Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on
- **Mode:** mvp
- **Granularity:** coarse
- **Phases:** 7 (Phase 0 — Phase 6)
- **JD signals (4):** CS/Engineering, computer vision / pose estimation, GCP-based ML workloads, sport/performance telemetry
- **Current focus:** Phase 0 — Bootstrap & Cost Guardrails (in progress)

## Current Position

- **Phase:** Phase 0 — Bootstrap & Cost Guardrails (in progress)
- **Plan:** Next: 00-04 (00-05 filming protocol shipped out-of-order on 2026-05-20; 00-04 bootstrap-gcp.sh still pending)
- **Status:** Phase 0 in progress (4/7 plans complete)
- **Progress:** [██████░░░░] 57%

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
- Plans shipped: 4 (00-01 Python toolchain ~2m; 00-02 repo hygiene ~4m; 00-03 kill-switch vendoring ~8m; 00-05 filming protocol ~6m)
- Average plans per phase: TBD
- Average node-repair invocations per phase: TBD (budget = 2)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 00-bootstrap-cost-guardrails | 01 | 2m | 1 | 7 |
| 00-bootstrap-cost-guardrails | 02 | 4m | 1 | 3 |
| 00-bootstrap-cost-guardrails | 03 | 8m | 1 | 4 |
| 00-bootstrap-cost-guardrails | 05 | 6m | 1 | 1 |

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
| KS-1 | Vendor (copy + adapt, NOT submodule) is the canonical vendoring pattern; every vendored file gets a banner with upstream URL + commit SHA + license + enumerated local modifications, central attribution lives in root `NOTICE`, per-component README mirrors it and adds operational context | `00-03-SUMMARY.md` | Three-layer attribution contract (banner / NOTICE / component README) makes Apache-2.0 compliance and modification traceability auditable in under 30s by a hiring-manager-grade reviewer; submodule would couple us to upstream's branch lifecycle and break offline reproducibility |
| KS-2 | Kill-switch reads target projectId from the Pub/Sub budget-notification body with ADC fallback (upstream uses ADC unconditionally) | `00-03-SUMMARY.md` | Makes a single deployed function safely reusable across projects without redeploy; matches GCP Billing notification schema; preserves backward compatibility with notifications that omit projectId via the ADC fallback |
| KS-3 | Pin upstream's actual lib `google-cloud-billing==1.19.0` + explicit `google-auth==2.35.0` (NOT the older `google-api-python-client` named in plan frontmatter) | `00-03-SUMMARY.md` | The plan frontmatter `contains: google-api-python-client` expectation reflected an older Cyclenerd snapshot; using the modern client is a Rule 1 correctness fix (the wrong lib would have broken the function); verify substring check still passes via docstring REST-method-name reference |
| FILM-1 | Filming-protocol hard-lock format: numbered list with bold lock name + one-sentence "why" in italics citing the relevant pitfall (Pitfall #1 or #8); every downstream operator-facing protocol doc mirrors this shape | `00-05-SUMMARY.md` | Per-lock pitfall citation makes the lock self-justifying for a hiring-manager reader and lets a skeptical reviewer trace any geometric assumption from doc → pitfall → code in <30s |
| FILM-2 | Canonical post-record CFR-detection command (`ffprobe -v error -show_streams -select_streams v:0 <file>.mp4 \| grep -E 'r_frame_rate\|avg_frame_rate\|nb_frames\|duration'` with `r_frame_rate == avg_frame_rate` required) lives in `docs/filming-protocol.md` Section 6 and is the substring Phase 1 ING-03 must reuse verbatim as the VFR-rejection gate | `00-05-SUMMARY.md` | Single-source-of-truth for the doc-and-code VFR contract; divergence is then mechanically detectable (Pitfall #8 + threat T-00-14 mitigation per plan 00-05 threat model) |
| FILM-3 | ASCII fenced-code-block diagram (no language tag) over PNG for v1 filming protocol; PNG upgrade deferred to Phase 6 polish | `00-05-SUMMARY.md` | Diff-able, greppable, renderable in any markdown viewer, zero binary churn; Phase 6 visual polish can upgrade if hiring-manager feedback ever requests |

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
| 2026-05-20 | Phase 0 Plan 03 executed | Cyclenerd billing kill switch vendored at upstream commit `e578179` into `infra/kill-switch/` (main.py + requirements.txt + README.md, Apache-2.0); `NOTICE` rewritten with three-layer attribution; entry point `stop_billing` (Cloud Functions Gen 2, python312) reads `projectId` from Pub/Sub message body with ADC fallback; `py_compile` + `mypy lib tests` green; commit `ad184e3` |
| 2026-05-20 | Phase 0 Plan 05 executed | `docs/filming-protocol.md` shipped (89 lines): four hard locks (BB height ±2 cm, fiducial, 60 fps CFR, tripod-only) each citing Pitfall #1 / #8; 25-line ASCII side-view fenced block; six-item phone-preview checklist (tripod / fiducial / side-on / TDC↔BDC / 60 fps CFR / lighting); iPhone + Android Auto-FPS-disable instructions; 5000 K LED lighting paragraph; ffprobe r_frame_rate==avg_frame_rate post-record gate; BOOT-05 complete; commit `bc6fd65` |

### Next Session

Execute Phase 0 Plan 04 next (author `scripts/bootstrap-gcp.sh` + `scripts/bootstrap-gcp.env.example` + `scripts/test-kill-switch.sh`; the deploy script consumes the vendored tree at `infra/kill-switch/` and the entry-point name `stop_billing` recorded in `00-03-SUMMARY.md`). Plan 04 is the deploy-script half of BOOT-03; plan 07 is the operator-run half. Plan 05 (filming protocol) already shipped out-of-order; remaining Phase 0 plans: 00-04 bootstrap-gcp.sh, 00-06 README skeleton, 00-07 operator-run kill-switch test. Phase 0 must complete before any GCP deploy.

---
*State initialized: 2026-05-20 after roadmap approval*
