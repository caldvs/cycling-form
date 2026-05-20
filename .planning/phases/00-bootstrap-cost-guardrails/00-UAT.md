---
status: partial
phase: 00-bootstrap-cost-guardrails
source: 00-01-SUMMARY.md, 00-02-SUMMARY.md, 00-03-SUMMARY.md, 00-04-SUMMARY.md, 00-05-SUMMARY.md, 00-06-SUMMARY.md
started: 2026-05-20T14:30:00Z
updated: 2026-05-20T15:05:00Z
---

## Current Test

[testing complete — autonomous scope; operator-run plan 00-07 deferred]

## Tests

### 1. Cold-start smoke (uv + lint + typecheck + tests)
expected: All four CI gates pass against the skeleton (ruff, ruff format check, mypy, pytest). Python is 3.12.x. lib/vision imports.
result: pass

### 2. GitHub Actions CI workflow valid
expected: .github/workflows/ci.yaml parses as valid YAML; uses astral-sh/setup-uv; runs ruff + mypy + pytest; triggered by push and PR to main; does NOT build/push containers (deferred to Phase 6).
result: pass

### 3. .gitignore blocks credentials, env, FIT, and large media
expected: `git check-ignore` blocks .env, secrets/cred.json, ride1.fit, data.parquet, video.mp4, .DS_Store. The negation `!.env.example` works (template stays trackable).
result: pass

### 4. README skeleton + JD-mapping table
expected: README.md contains the title, a 4-row JD-mapping table with `placeholder` status cells (CS/Eng, CV/pose, GCP ML, sport telemetry), CI badge URL using workflows/ci.yaml/badge.svg, links to docs/filming-protocol.md and infra/kill-switch/, and the "What this does NOT do" section header for Phase 6 to fill.
result: pass

### 5. Filming protocol locks the four hard invariants
expected: docs/filming-protocol.md exists with the six-item checklist, an ASCII side-view diagram (fenced code block), the four hard locks (BB height, fiducial, 60fps, CFR mandatory), iPhone + Android instructions for disabling Auto/Smart FPS, the 5000K LED lighting guidance, and the tripod-only mandate.
result: pass

### 6. Kill-switch source vendored from Cyclenerd
expected: infra/kill-switch/main.py + requirements.txt + README.md exist. NOTICE credits Cyclenerd/poweroff-google-cloud-cap-billing with commit SHA e5781791... and Apache-2.0 license. main.py has zero hard-coded project ids — project comes from the Pub/Sub event payload. main.py compiles cleanly.
result: pass

### 7. GCP bootstrap scripts ready for operator
expected: scripts/bootstrap-gcp.env.example (with us-central1 default + EU-override note), scripts/bootstrap-gcp.sh (idempotent gcloud setup), scripts/test-kill-switch.sh (end-to-end verifier with KILL-SWITCH TEST: PASS gate). All three pass `bash -n` syntax check; required content (set -euo pipefail, the three budget thresholds 50/90/100, the billing APIs) all present.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]

## Operator-Only Tests Deferred

Plan 00-07 (BOOT-02 GCP project + BOOT-03 kill switch deployed-and-tested + BOOT-04 region pin verified in live resources) requires you to run `scripts/bootstrap-gcp.sh` and `scripts/test-kill-switch.sh` against a real GCP billing account. These are NOT in this UAT — they need their own verification pass after you complete the operator runbook documented in the previous turn.

When you've run those scripts, mark BOOT-02/03/04 complete in REQUIREMENTS.md and re-run `/gsd:verify-work 0` to confirm full Phase 0 closure (or just accept Phase 0 as "autonomous work complete, operator pending").
