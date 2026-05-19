# Phase 0: Bootstrap & Cost Guardrails - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 0-Bootstrap & Cost Guardrails
**Areas discussed:** GCP provisioning method, Kill switch sourcing, Default region, Local credentials handling, Filming protocol detail, README JD-mapping layout, CI scope in Phase 0, Repo visibility
**Mode:** --auto (recommended option auto-selected per area; no interactive prompts)

---

## A. GCP Provisioning Method

| Option | Description | Selected |
|--------|-------------|----------|
| gcloud setup script | Documented idempotent shell script committed to `scripts/bootstrap-gcp.sh` | ✓ |
| Terraform | Full IaC with `.tf` files, state in GCS | |
| Pulumi / OpenTofu | Alternative IaC | |

**User's choice (auto):** gcloud setup script
**Notes:** IaC for one project + one region is over-engineering and dilutes the JD signal. The resume value is the kill switch + budget architecture, not Terraform fluency.

---

## B. Kill Switch Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| Vendor Cyclenerd reference | Copy + adapt `Cyclenerd/poweroff-google-cloud-cap-billing` into `infra/kill-switch/`; credit upstream in NOTICE | ✓ |
| From scratch | Build Pub/Sub topic + Cloud Function originally | |
| Git submodule | Reference upstream via submodule | |

**User's choice (auto):** Vendor + adapt
**Notes:** Battle-tested; faster; easy to credit. Submodule would fragment the portfolio repo.

---

## C. Default Region

| Option | Description | Selected |
|--------|-------------|----------|
| us-central1 | All services available, cheapest egress, BQ-US alignment, canonical | ✓ |
| europe-west1 | Closer for UK/EU users; still full-service | |
| asia-southeast1 | Closest for APAC users | |

**User's choice (auto):** us-central1 (with documented `GCP_REGION` env override)
**Notes:** Override path documented for EU users; the choice must be locked before any service is created since region cannot change in-place.

---

## D. Local Credentials Handling

| Option | Description | Selected |
|--------|-------------|----------|
| ADC (gcloud auth application-default) | Standard local-dev path on macOS; no JSON files in repo | ✓ |
| Service-account JSON | Required for CI; deferred to Phase 6 for that purpose | |
| Workload Identity Federation | Production-grade; overkill for solo portfolio | |

**User's choice (auto):** ADC for local; SA-JSON deferred to Phase 6
**Notes:** Avoid carrying credential material before there's a use for it.

---

## E. Filming Protocol Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Concise checklist + one labeled diagram | One-pager covering camera height, fiducial, 60fps, CFR, tripod | ✓ |
| Comprehensive multi-page spec | Full photography textbook with lighting calibration, white balance, etc. | |
| Bullet list only | No diagram | |

**User's choice (auto):** Concise one-pager
**Notes:** Locks the four critical pitfall-#1 invariants without becoming a textbook. Bad-example annotations deferred to Phase 1 when real footage exists.

---

## F. README JD-Mapping Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Table (one row per JD area) | Skimmable, audit-friendly | ✓ |
| Prose paragraphs | More readable, but hides mapping | |
| Checklist | Looks like a TODO, not a deliverable | |

**User's choice (auto):** Table
**Notes:** Sits ABOVE the architecture diagram so a hiring manager reads it first.

---

## G. CI Scope in Phase 0

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal lint+test CI now | `ruff` + `mypy` + `pytest` on push/PR; build/push deferred to Phase 6 | ✓ |
| Defer all CI to Phase 6 | No CI in Phase 0 | |
| Full CI now (lint+test+build+push) | Adds container build before images exist | |

**User's choice (auto):** Minimal CI in Phase 0; build+push deferred to Phase 6 (PORT-05)
**Notes:** CI badge live from day 1 is high-signal at near-zero cost. Build/push has no inputs in Phase 0.

---

## H. Repo Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Public from day 1 | Every commit serves the portfolio narrative | ✓ |
| Private until Phase 6 | Wait until "it's good" | |

**User's choice (auto):** Public from day 1
**Notes:** Portfolio value compounds with visibility. Secrets enforced gitignored.

---

## Claude's Discretion

- File and directory naming conventions inside `scripts/`, `infra/`, `docs/`, `lib/`
- Specific dev-tool pins beyond the locked stack (`pytest-cov` etc.)
- ASCII vs simple PNG diagram in filming protocol
- Whether to add `pyproject.toml` script entrypoints

## Deferred Ideas

- Multi-environment GCP projects (dev/staging/prod)
- Pre-commit hooks (ruff/mypy on commit)
- Cost dashboard screenshot in README (Phase 6 deliverable)
- `docs/filming-protocol-bad-examples.md` — defer to Phase 1
- PNG/SVG diagram upgrade — defer until requested
- `pyproject.toml` script entrypoints — add only when code lands
- GitHub repo templates (issue/PR templates) — defer to Phase 6
