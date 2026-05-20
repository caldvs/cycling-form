---
phase: 00-bootstrap-cost-guardrails
plan: 02
subsystem: infra
tags:
  - gitignore
  - repo-hygiene
  - privacy
  - secrets
  - contributing
  - notice
  - boot-07
  - public-repo
  - portfolio

# Dependency graph
requires:
  - phase: 00-bootstrap-cost-guardrails
    provides: "Plan 00-01 created a minimal `.gitignore` covering only `.venv/` + tool caches; this plan OVERWRITES it with the full BOOT-07 / D-14 pattern set"
provides:
  - "Full project-wide `.gitignore` covering credentials (`*.json`, `.env`, `.env.*`, `secrets/`, `*.pem`, `*.key`), raw telemetry with GPS (`*.fit`, `*.FIT`, `*.tcx`, `*.gpx`), large fixture artifacts (`*.mp4`, `*.mov`, `*.avi`, `*.parquet`), Python build/cache output, OS/editor noise"
  - "`!.env.example` negation that keeps committed env templates (e.g. `scripts/bootstrap-gcp.env.example`, D-03) trackable while the real `.env` is blocked"
  - "`CONTRIBUTING.md` with dev quickstart (uv install + `uv sync` + four CI gates), repo conventions, and a load-bearing `Never commit secrets` section (D-27) documenting ADC auth, env-template path, raw-FIT GPS hazard, and the rotate-and-scrub procedure"
  - "`NOTICE` stub placeholder for upstream credit (plan 00-03 will populate with the Cyclenerd kill-switch attribution per D-04)"
affects:
  - "Plan 00-03 (vendor Cyclenerd) — overwrites `NOTICE` with real attribution; the placeholder block in this stub explicitly signposts that handoff"
  - "Plan 00-04 (bootstrap-gcp scripts) — relies on the `!.env.example` negation so `scripts/bootstrap-gcp.env.example` ships while `scripts/bootstrap-gcp.env` stays gitignored"
  - "Every later phase that handles real ride data — the `*.fit`/`*.tcx`/`*.gpx` privacy block applies repo-wide"
  - "Phase 3 (BigQuery schemas) — blanket `*.json` rule will need a `!infra/bigquery/schemas/*.json` negation when committed JSON schemas land; the in-file NOTE comment flags this"
  - "Phase 6 (PORT-01) — the README contribution section can link to `CONTRIBUTING.md` rather than duplicating dev-setup instructions"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anchored deny-all + targeted negation pattern: blanket `*.json` repo-wide with documented intent to re-allow specific JSON via `!path/to/*.json` in later phases. Avoids leaving service-account JSON shaped files trackable by default at the cost of one extra negation line whenever genuine JSON ships."
    - "`!.env.example` negation as the canonical pattern for 'show the template, hide the real env' — applies to any future `*.env.example` file at any path"
    - "Case-pair globs for telemetry (`*.fit` AND `*.FIT`) — defensive for case-sensitive filesystems (Linux CI runners) where macOS-developed filenames may diverge from the on-disk casing"
    - "Grouped `.gitignore` with header comments per category (Credentials/env, Sport-telemetry privacy, Large media, Python, Tool caches, OS/editor) — keeps the file readable and makes the intent of each rule obvious to future contributors and to LLM code review"
    - "Load-bearing one-liner doc convention: `CONTRIBUTING.md` has a `## Never commit secrets` H2 (not a buried bullet) because public-repo secret hygiene is the single most expensive forever-mistake on this project"

key-files:
  created:
    - CONTRIBUTING.md
    - NOTICE
  modified:
    - .gitignore  # overwritten — replaces 00-01's minimal stub with full BOOT-07 / D-14 pattern set

key-decisions:
  - "Anchored vs unanchored `*.json`: kept the blanket repo-wide rule (per D-14) rather than anchoring to `/*.json` only at the root. Rationale: defense-in-depth — a service-account JSON dropped in any subdirectory (e.g. `scripts/key.json`, `infra/sa.json`) is silently blocked, not just root-level ones. The cost is one explicit negation per legitimately-committed JSON family (e.g. `!infra/bigquery/schemas/*.json`), which is acceptable. The in-file NOTE comment documents this for future plan owners."
  - "Included `*.pem` and `*.key` in the credentials group even though they were not in the D-14 list verbatim. Rationale: private-key file extensions are universally secret-shaped; cost is zero (no legitimate use case in this repo); benefit is one more layer of defense-in-depth against accidental commits."
  - "Included `*.tcx` and `*.gpx` alongside `*.fit` in the privacy group even though D-14 names only `*.fit`. Rationale: BOOT-07's privacy concern is GPS-bearing raw telemetry, and TCX/GPX are equally GPS-bearing alternative formats from the same family of devices. Same threat model, same mitigation."
  - "Used a single H2 `## Never commit secrets` in `CONTRIBUTING.md` (per D-27) rather than scattering the policy across multiple sections. Rationale: D-27 calls for one load-bearing note; a single labelled H2 is the most scannable form and is exactly what future contributors (including Claude executors) will Ctrl-F for."

patterns-established:
  - "Grouped `.gitignore` shape (with category-header comments) — every future plan that needs to add ignore patterns SHOULD extend the relevant group rather than appending bare lines, to keep the file scannable"
  - "Public-repo secret-hygiene contract: `.gitignore` is the enforcement layer; `CONTRIBUTING.md` §Never-commit-secrets is the documentation layer; both must stay in sync (if a new secret-shaped artifact emerges, both files get updated in the same plan)"
  - "Stub-with-signpost convention: `NOTICE` is intentionally placeholder content with an inline `(vendored components will be listed here as they are added — see plan 00-03)` marker so the next plan owner knows exactly where their content goes. Same convention used by 00-01's stub README."

requirements-completed:
  - BOOT-07

# Metrics
duration: 4m
completed: 2026-05-20
---

# Phase 0 Plan 02: Repo Hygiene Summary

**Public-repo secret-hygiene baseline: full BOOT-07 `.gitignore` (credentials, raw FIT/TCX/GPX with GPS, large fixture artifacts, Python/tool caches), `CONTRIBUTING.md` with load-bearing `Never commit secrets` H2 (D-27), and a `NOTICE` stub signposted for the plan 00-03 Cyclenerd attribution.**

## Performance

- **Duration:** ~4 min wall clock
- **Started:** 2026-05-20T12:53:00Z (approx)
- **Completed:** 2026-05-20T12:57:00Z
- **Tasks:** 1 (Task 1: write `.gitignore`, `CONTRIBUTING.md`, `NOTICE`)
- **Files modified:** 3 (1 overwritten + 2 created)

## Accomplishments

- `.gitignore` overwritten with the full BOOT-07 / D-14 pattern set: 30+ patterns across 6 grouped categories (Credentials/env, Sport-telemetry privacy, Large media, Python, Tool caches, OS/editor)
- `!.env.example` negation in place — `scripts/bootstrap-gcp.env.example` (D-03, plan 00-04 deliverable) will be trackable while `scripts/bootstrap-gcp.env` is blocked
- `CONTRIBUTING.md` written with H2 sections: `Local development quickstart` (uv install → `uv sync` → 4-gate run), `Repo conventions` (Python 3.12 lock, uv-only, CLAUDE.md cross-reference), load-bearing `Never commit secrets` (ADC-only auth path, env-template guidance, raw FIT/TCX/GPX privacy, rotate-and-scrub procedure), `Bug reports and issues`
- `NOTICE` written as a minimal stub with explicit `(vendored components will be listed here as they are added — see plan 00-03)` signpost
- All six `git check-ignore` behavior tests pass: `.env` blocked, `foo.fit` blocked, `.env.example` not blocked (negation works at both root and under `scripts/`), `secrets/cred.json` blocked, `*.pem`/`*.key` blocked
- Zero test artifacts left in working tree after verification

## Task Commits

1. **Task 1: Write `.gitignore`, `CONTRIBUTING.md`, `NOTICE`** — `523111a` (`feat`)

**Plan metadata commit:** to follow (this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md updates)

## Files Created/Modified

- `.gitignore` — overwritten. Replaces 00-01's minimal-stub (`.venv/` + tool caches only) with the full BOOT-07 / D-14 pattern set. 6 grouped categories, 32 patterns + 1 negation + 2 NOTE comments.
- `CONTRIBUTING.md` — created. Four H2 sections; load-bearing `Never commit secrets` H2 per D-27.
- `NOTICE` — created. Minimal stub; plan 00-03 will populate with the Cyclenerd kill-switch upstream credit.

## Decisions Made

- **Blanket `*.json` vs anchored `/*.json`:** chose blanket (per D-14 verbatim). The execution-context note suggested anchoring with `/*.json`, but the plan's `<action>` block explicitly specifies the unanchored form and documents the trade-off in an in-file `# NOTE` comment. Following the plan's stated intent: defense-in-depth across all subdirectories, with negation-per-need in later phases.
- **Added `*.pem` + `*.key` to credentials group:** the plan's action block lists these explicitly. Universally secret-shaped extensions; zero cost to include.
- **Added `*.tcx` + `*.gpx` to telemetry-privacy group:** the plan's action block lists these explicitly. Same GPS-privacy threat model as `*.fit`.
- **Included `node_modules/` defensively:** the plan's action block calls for it. Future tooling may need it; zero cost.

## Deviations from Plan

None — the plan was executed exactly as written. All patterns in the `<action>` block were written verbatim; all in-file `# NOTE` comments specified by the plan are in place; all six verification tests pass.

The plan's `<action>` block already accounted for the apparent conflict between the execution-context note ("use a leading `/` to anchor: `/*.json`") and D-14 (blanket `*.json`) by specifying the blanket form with an explanatory comment. The plan's instruction "If the plan specifies a different exact pattern set, follow the plan" was followed.

## Issues Encountered

None.

## Threat Surface Scan

No new threat surface introduced. This plan's mitigations match the plan's `<threat_model>` exactly:

- **T-00-03 (Info disclosure, `.env`):** mitigated by `.env` + `.env.*` + `!.env.example` rules — verified via `git check-ignore .env` returning 0.
- **T-00-04 (Info disclosure, raw FIT with GPS):** mitigated by `*.fit` + `*.FIT` + `*.tcx` + `*.gpx` — verified via `git check-ignore foo.fit` returning 0; `CONTRIBUTING.md` documents the privacy rationale.
- **T-00-05 (Info disclosure, SA JSON):** mitigated by blanket `*.json` — verified via `git check-ignore secrets/cred.json` returning 0; `CONTRIBUTING.md` documents ADC as the only Phase-0 auth path.
- **T-00-06 (Repudiation, accidental secret commit):** accepted — `CONTRIBUTING.md` §Never-commit-secrets documents the rotate-and-scrub procedure (`git filter-repo` or BFG, then force-push after rotation).

No additional threats introduced. All three files are pure documentation/config — no executable code paths created.

## Known Stubs

| File     | Reason                                                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `NOTICE` | Minimal placeholder. Plan 00-03 (vendor Cyclenerd kill-switch into `infra/kill-switch/` per D-04) will overwrite this with the upstream credit. The in-file `(vendored components will be listed here as they are added — see plan 00-03)` signpost makes the handoff explicit. |

The `.gitignore` blanket `*.json` rule is annotated as a forward-compatibility item (NOT a stub): the in-file `# NOTE: blanket *.json — re-allow specific JSON via !path in later phases` comment flags Phase 3 schema commits as the trigger for adding negation lines. This is intentional defense-in-depth, not unfinished work.

## Patterns Added Beyond the Quality-Gate List

Per the `<output>` note in the plan, here are the gitignore patterns added beyond the D-14 / quality-gate minimum so later phases know what's already covered:

- **Editor swap files:** `*.swp` — covers Vim swap files left behind by `:e`/crashes
- **JetBrains IDE config:** `.idea/`
- **VS Code workspace config:** `.vscode/`
- **macOS metadata:** `.DS_Store` (in D-14) **plus** `Thumbs.db` for Windows interop
- **Defensive npm/node:** `node_modules/` — covers any future Node tooling that may land (e.g. mermaid CLI for architecture diagrams in Phase 6)
- **Private-key extensions:** `*.pem`, `*.key` — universal secret-shaped extensions beyond D-14's `*.json` / `.env` list
- **TCX/GPX telemetry:** `*.tcx`, `*.gpx` — same GPS-privacy threat model as `*.fit`; D-14 named only `*.fit`
- **Case-sensitive FIT:** `*.FIT` (uppercase) — defensive for Linux CI runners
- **Video formats:** `*.mov`, `*.avi` — companions to D-14's `*.mp4` for large media
- **Build outputs:** `*.egg-info/`, `*.egg`, `build/`, `dist/`, `venv/` — Python build/dist outputs beyond D-14's `.venv` + `__pycache__`
- **Coverage reports:** `.coverage`, `htmlcov/` — already covered by 00-01 minimal stub; re-included here for completeness

Later plans MUST NOT re-add any of these; just extend with whatever new artifact-type they introduce.

## User Setup Required

None — this plan is pure repo-hygiene config, no external services touched.

## Next Phase Readiness

- Plan 00-03 (vendor Cyclenerd kill-switch) can drop the upstream tree into `infra/kill-switch/` and overwrite `NOTICE` with the attribution; the `.gitignore` rules are already in place to block any incidentally-included secrets in the vendored tree
- Plan 00-04 (`scripts/bootstrap-gcp.env.example` + bootstrap shell scripts) can ship the env template — `!.env.example` negation is verified working
- Public repo (D-25) is safe to push: `.env`, `*.fit`, `*.pem`, `*.key`, `secrets/`, and any stray `*.json` are all blocked from commit #1 onward
- `CONTRIBUTING.md` is in place for future PR templates / external-reader entry points; Phase 6 (PORT-01) README work can link to it rather than duplicating dev-setup steps

## Self-Check: PASSED

All claimed files exist on disk:
- `/Users/callum/software-local/vision/.gitignore`
- `/Users/callum/software-local/vision/CONTRIBUTING.md`
- `/Users/callum/software-local/vision/NOTICE`
- `/Users/callum/software-local/vision/.planning/phases/00-bootstrap-cost-guardrails/00-02-SUMMARY.md`

Claimed commit exists in git log:
- `523111a` — `feat(00-02): add repo hygiene gitignore, CONTRIBUTING, NOTICE stub`

All six gitignore behavior tests passed during verification:
- `.env` ignored (T-00-03 mitigation)
- `foo.fit` ignored (T-00-04 mitigation)
- `.env.example` NOT ignored at root (negation works)
- `scripts/bootstrap-gcp.env.example` NOT ignored under subdirectory (negation works at depth)
- `secrets/cred.json` ignored (T-00-05 mitigation)
- `*.pem` + `*.key` ignored (defense-in-depth)

---
*Phase: 00-bootstrap-cost-guardrails*
*Plan: 02 — Repo hygiene (.gitignore, CONTRIBUTING.md, NOTICE stub)*
*Completed: 2026-05-20*
