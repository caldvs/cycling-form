---
phase: 00-bootstrap-cost-guardrails
plan: 06
subsystem: docs+ci
tags: [docs, ci, portfolio, github-actions, uv, ruff, mypy, pytest, readme, jd-mapping, badge]

# Dependency graph
requires:
  - phase: 00-bootstrap-cost-guardrails
    provides: "Plan 00-01 — pyproject.toml + uv.lock + ruff/mypy/pytest dev group + lib/vision/ package layout (the gates this CI exercises and the readme = README.md reference this README now satisfies)"
  - phase: 00-bootstrap-cost-guardrails
    provides: "Plan 00-04 — scripts/bootstrap-gcp.sh + scripts/bootstrap-gcp.env.example (referenced from README GCP-setup section)"
  - phase: 00-bootstrap-cost-guardrails
    provides: "Plan 00-05 — docs/filming-protocol.md (referenced from README filming-protocol section)"
provides:
  - "README.md — JD-bullet → code mapping table with four placeholder rows (CS/Engineering, Computer vision / pose estimation, GCP-based ML workloads, Sport/performance telemetry) sitting above the architecture-diagram placeholder; one-paragraph project intro; cost-story + filming-protocol + local-dev + GCP-setup + layout + license sections"
  - "'What this does NOT do' section header seeded in README (empty body) for Phase 6 (PORT-02) to fill from REQUIREMENTS § Out of Scope"
  - ".github/workflows/ci.yaml — green-after-first-commit CI exercising ruff check + ruff format --check + mypy lib tests + pytest -q on push/PR to main (Python 3.12, ubuntu-latest, 10-min timeout)"
  - "CI badge URL pattern `https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yaml/badge.svg` — Phase 6 PORT-01 replaces the placeholders once the public repo URL is live"
affects:
  - "ROADMAP Phase 0 success criterion #5 (README skeleton with JD-mapping table + lint+test CI badge live)"
  - "Phase 6 PORT-01 (final fills of JD-mapping Status cells), PORT-02 (anti-features bullets under the seeded header), PORT-04 (architecture diagram replacing the placeholder), PORT-05 (extends the same workflow file with container build/push — must not break the badge URL)"
  - "BOOT-01 CI half (lint+type+test workflow) and BOOT-06 (README skeleton) both met"

# Tech tracking
tech-stack:
  added:
    - "GitHub Actions workflow (`.github/workflows/ci.yaml`) — first piece of automation in the repo"
    - "astral-sh/setup-uv@v3 action pinned to `version: '0.4.x'` — matches the local uv version range, enables uv's GitHub-Actions native cache keyed on pyproject.toml + uv.lock"
  patterns:
    - "Top-of-README CI badge — green-after-first-commit portfolio signal (D-23); badge URL pattern is the single source of truth that Phase 6 PORT-05 must not break when it appends a build+push job"
    - "JD-bullet → code mapping table as load-bearing portfolio device — sits ABOVE the architecture diagram (D-18, CONTEXT §specifics: hiring manager reads top-down); Status column is the ledger that fills in over Phases 1→6"
    - "Section-header seeding — README's 'What this does NOT do' header exists in Phase 0 even with empty body so Phase 6 (PORT-02) can append without restructuring the doc"
    - "Read-only `permissions: contents: read` at the workflow root — least-privilege default; explicit grants would be added by Phase 6 PORT-05 when build+push needs `packages: write`"
    - "Dependency-glob cache key (`pyproject.toml` + `uv.lock`) — invalidates the uv cache on any pin change without manual cache busting"

key-files:
  created:
    - ".github/workflows/ci.yaml"
  modified:
    - "README.md (overwrote 3-line stub from plan 00-01 with the full 85-line skeleton)"

key-decisions:
  - "Pinned `astral-sh/setup-uv@v3` further with `version: '0.4.x'` in the `with:` block — the action is at v3 (mitigates T-00-16 tampering) and the minor-range pin keeps the installed uv binary reproducible across CI runs without locking out patch fixes; SHA-pinning of the action itself is deferred to Phase 6 PORT-05 hardening per the threat-model `accept` disposition on T-00-SC"
  - "Set `timeout-minutes: 10` on the only job — T-00-18 (DoS via long-running test hangs) mitigation; comfortably above the ~30 s the current empty test suite needs and below the GitHub Actions free-tier per-job cap"
  - "Used `cache-dependency-glob` multi-line YAML (both `pyproject.toml` AND `uv.lock`) rather than just `uv.lock` — pyproject changes alone (e.g., a new dev dep) should invalidate the cache before the lock catches up"
  - "Wrote the README with `<OWNER>/<REPO>` placeholders in the badge URL plus an HTML comment flagging them as Phase 6 PORT-01 follow-ups — README is committed before the public GitHub repo URL exists (D-25..D-26: public-from-day-1, URL recorded in PROJECT.md once created), so a syntactically valid URL with TODO markers is the right shape"
  - "Seeded the 'What this does NOT do' section with a one-line lead-in (vs. truly empty) — D-20 mandates the header exists in Phase 0 'even if empty body'; the lead-in plus an HTML comment tells the next agent unambiguously where to append, while not committing to any anti-feature claim before PORT-02 runs"
  - "Layout block uses a single fenced ```text``` code block rather than a tree command's literal output — diff-able, no binary characters, and the trailing per-line comment naming the owning phase (Phase 0 / Phase 2 / Phase 5) doubles as a roadmap signpost"

patterns-established:
  - "Per-task conventional-commit format scoped by phase-plan (`ci(00-06): ...`, `docs(00-06): ...`) — keeps `git log --oneline` skimmable as a phase audit trail"
  - "CI workflow steps in lint → format → type → test order — fast feedback (lint fails first, cheapest); plan-01's pyproject already orders the gates this way and the workflow mirrors it"
  - "Anti-features header seeding pattern — when a doc section exists in spec but its content is owned by a later phase, seed the H2 + a one-line lead-in + HTML comment marker, never leave a true vacuum"

requirements-completed: [BOOT-01, BOOT-06]

# Metrics
duration: 8min
completed: 2026-05-20
---

# Phase 0 Plan 06: README Skeleton + GitHub Actions CI Summary

**Replaced the 3-line README stub with the load-bearing portfolio README — JD-bullet → code mapping table (four placeholder rows above the architecture-diagram placeholder), CI badge, cost story, filming-protocol link, local-dev quickstart, GCP-setup forward-reference, layout signposts — and added the first GitHub Actions workflow (ruff check + ruff format --check + mypy + pytest on push/PR to main, Python 3.12, 10-min timeout, read-only token, astral-sh/setup-uv@v3 pinned to 0.4.x). BOOT-01 CI side and BOOT-06 both met; ROADMAP Phase 0 success criterion #5 satisfied.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-20T14:15:00Z (approximate)
- **Completed:** 2026-05-20T14:23:00Z
- **Tasks:** 2 (both `type="auto"`, both completed, both committed)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write README.md skeleton with JD-mapping table | `2a81a0a` | `README.md` (overwrote 3-line stub → 85 lines) |
| 2 | Write .github/workflows/ci.yaml (ruff + mypy + pytest on push/PR) | `d03cd4b` | `.github/workflows/ci.yaml` (new, 51 lines) |

## What Was Built

### README.md (85 lines, in the 60–200 acceptance band)

Top-down structure (hiring manager reads top-down per CONTEXT §specifics):

1. **H1 title + CI badge** — `# Vision — Cycling Form & Performance Analyzer`; badge URL `https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yaml/badge.svg` linking to the workflow file; HTML-comment TODO above the badge flags Phase 6 PORT-01 placeholder substitution.
2. **One-paragraph project intro** — names the four JD areas; cites the canonical "knee-over-pedal-spindle drift correlates with power drop after minute 20" example from PROJECT.md; explicitly scopes-out multi-tenant / real-time / coaching prescriptions.
3. **JD-bullet → code mapping** (H2, the load-bearing table per D-18) — four data rows (CS/Engineering, Computer vision / pose estimation, GCP-based ML workloads, Sport/performance telemetry), all with `Status: placeholder` (D-19); each row's "Code/doc references" pre-cites the file paths that later phases will fill.
4. **What this does NOT do** (H2, D-20) — header exists with a one-line lead-in + HTML comment marker; bullet list deliberately empty for Phase 6 PORT-02.
5. **Architecture** (H2) — one paragraph describing the four-stage Cloud Run Jobs pipeline (pose → fit → features → correlate); HTML-comment placeholder line for the Phase 6 PORT-04 diagram embed; links `.planning/research/ARCHITECTURE.md` as the interim design contract.
6. **Cost story** (H2) — $20/mo cap, 50/90/100% alerts, Pub/Sub → Cloud Function kill switch (Cyclenerd, Apache-2.0), `--min-instances=0`; links `infra/kill-switch/README.md`.
7. **Filming protocol** (H2) — one paragraph naming the four hard locks; links `docs/filming-protocol.md`.
8. **Local development** (H2) — three fenced `bash` code blocks: install uv, `uv sync`, `uv run ruff check . && uv run mypy lib tests && uv run pytest -q`.
9. **GCP setup (Phase 0)** (H2) — three-step numbered list (cp env.example → fill values → `./scripts/bootstrap-gcp.sh`); warning line referencing `./scripts/test-kill-switch.sh` and `infra/kill-switch/README.md`.
10. **Layout** (H2) — fenced `text` block, 18 path-lines each carrying a trailing comment noting which phase owns the path; covers Phase 0 deliverables and forward-looking entries for `pipeline/{pose,fit,features,correlate}/`, `viewer/`, `.planning/`.
11. **License & credits** (H2) — MIT (matches `pyproject.toml`); vendored components → see `NOTICE` (currently Cyclenerd kill switch, Apache-2.0).

### .github/workflows/ci.yaml (51 lines)

- `name: CI`
- Triggers: `push` to `branches: [main]` and `pull_request` to `branches: [main]`
- Top-level `permissions: contents: read` (least-privilege; T-00-17 mitigation)
- Single job `ci` (label: `ruff + mypy + pytest (Python 3.12)`) on `ubuntu-latest`, `timeout-minutes: 10` (T-00-18 mitigation)
- Steps (in order):
  1. `actions/checkout@v4`
  2. `astral-sh/setup-uv@v3` with `version: "0.4.x"`, `enable-cache: true`, `cache-dependency-glob: pyproject.toml | uv.lock`
  3. `uv python install 3.12`
  4. `uv sync --frozen`
  5. `uv run ruff check .`
  6. `uv run ruff format --check .`
  7. `uv run mypy lib tests`
  8. `uv run pytest -q`
- Validated as YAML: `uv run --with pyyaml python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yaml'))"` exits 0; structure inspected (triggers, job names, step names, timeout, permissions all as specified).
- Verified NOT present: `docker build`, `docker push`, `gcr.io`, `artifactregistry` (deferred to Phase 6 PORT-05 per D-22).

## Decisions Made

(See frontmatter `key-decisions` for the canonical list.) Headline:

- Pinned `astral-sh/setup-uv@v3` further to `version: "0.4.x"` to lock the installed uv binary across CI runs while accepting upstream's `@v3` major-pin (SHA-pinning deferred to Phase 6 PORT-05 per the threat model's `accept` disposition on T-00-SC).
- Wrote README with `<OWNER>/<REPO>` placeholders + HTML-comment TODO rather than guessing the future repo URL — public repo URL is captured in PROJECT.md when created per D-25..D-26.
- Seeded the "What this does NOT do" header with a one-line lead-in + HTML comment (vs. truly empty) so the next agent has a stable insertion point.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' `<verify>` and `<acceptance_criteria>` blocks passed first-try:

- README: 85 lines (in 60–200 band), 4 `| placeholder |` cells, JD-table appears before `## Architecture`, all required strings present (`workflows/ci.yaml/badge.svg`, `uv sync`, `bootstrap-gcp.sh`, `test-kill-switch.sh`, `docs/filming-protocol.md`, `What this does NOT do`, `Vision`, four JD-area labels), fenced-code-block markers balanced (0 leftover).
- CI: file exists, parses as YAML, all required strings present (`astral-sh/setup-uv`, `uv sync --frozen`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy lib tests`, `uv run pytest -q`, `branches: [main]`, `ubuntu-latest`, `timeout-minutes:`), and the negative check (`docker build|docker push|gcr.io|artifactregistry`) returned no matches.

## CI Badge URL Pattern (forward-reference for Phase 6 PORT-05)

The README badge URL is:

```
https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yaml/badge.svg
```

linking to:

```
https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yaml
```

Phase 6 PORT-05 will append a container build+push job to the same `ci.yaml` workflow. To preserve the badge, PORT-05 MUST keep the workflow filename `ci.yaml` and MUST keep at least one job that runs on push to `main` (the badge reflects the most-recent workflow run on the default branch). The badge URL itself does not need updating — it is keyed on the workflow filename, not on its job structure.

## Action-version pins recorded

| Action | Pin used here | Phase 6 PORT-05 may bump? |
|---|---|---|
| `actions/checkout` | `@v4` | Yes — bump deliberately when v5 stabilizes |
| `astral-sh/setup-uv` | `@v3`, `version: "0.4.x"` | Yes — when local uv moves to 0.5.x, bump both the action major and the `version:` minor in lock-step |

SHA-pinning of both actions is deferred to Phase 6 PORT-05 hardening (T-00-SC accept disposition).

## Self-Check: PASSED

- README.md exists (85 lines, in 60–200 band, all required strings present, 4 placeholder rows, JD-table before Architecture).
- .github/workflows/ci.yaml exists (parses as YAML; contains setup-uv, uv sync --frozen, ruff check, ruff format --check, mypy lib tests, pytest -q; branches [main]; ubuntu-latest; timeout-minutes; no container-build steps).
- Commit `2a81a0a` exists on `main` (README task).
- Commit `d03cd4b` exists on `main` (CI workflow task).
- Both tasks committed via per-task commits per the plan's `<done>` step.
- BOOT-01 (CI half) and BOOT-06 marked complete; ROADMAP Phase 0 success criterion #5 satisfied.
