# Phase 0: Bootstrap & Cost Guardrails - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 0 delivers the project's foundation **before any compute, ML, or domain code is written**: a reproducible Python toolchain, a cost-bounded GCP project with a tested billing kill switch, a documented filming protocol that locks the geometry downstream pose work will depend on, and a README skeleton with the JD-bullet → code mapping table that later phases fill in. The phase ends when a budget overrun cannot drain the wallet and a future developer (or hiring manager) can read the repo and understand both the discipline and the safety net before any service exists.

**In scope (BOOT-01..07):** Python 3.12 + uv toolchain, GCP project with $20/mo budget + alerts at 50/90/100%, Pub/Sub → Cloud Function kill switch deployed and tested, single region pinned, `docs/filming-protocol.md`, README skeleton with JD-mapping table, `.gitignore` covering credentials/env/raw-FIT-with-GPS.

**Out of scope (deferred):** Any container builds (Phase 2), any GCS/BQ writes (Phase 3), any Workflows/Eventarc (Phase 4), any viewer (Phase 5), any GitHub Actions build/push (Phase 6 — PORT-05); a minimal ruff/mypy/pytest CI badge is in scope here.

</domain>

<decisions>
## Implementation Decisions

### A. GCP Provisioning Method
- **D-01:** Use a documented `gcloud` setup script (`scripts/bootstrap-gcp.sh`) committed to the repo. NOT Terraform / Pulumi / OpenTofu.
- **D-02:** Script is idempotent — running it twice produces the same final state. Use `gcloud ... --quiet || true` patterns with explicit existence checks before create commands.
- **D-03:** Configuration values (project id, region, budget amount, alert email) live in a `scripts/bootstrap-gcp.env.example` template; the real `.env` file is gitignored.

**Rationale:** IaC for one project + one region is over-engineering and dilutes the JD signal. The resume value is the kill switch + budget architecture, not Terraform fluency. A shell script keeps the cognitive cost low and is the documented Google-recommended quickstart pattern.

### B. Kill Switch Sourcing
- **D-04:** Vendor (copy + adapt) the `Cyclenerd/poweroff-google-cloud-cap-billing` reference repo into `infra/kill-switch/`. Credit upstream in `NOTICE` and link in README.
- **D-05:** The kill switch is a Pub/Sub topic + Cloud Function (Gen 2) that, on receiving a `budgetAmount > thresholdAmount` notification from the GCP Billing budget, calls `cloudbilling.projects.updateBillingInfo` to disable billing on the project.
- **D-06:** The kill switch MUST be tested end-to-end on a throwaway project before Phase 0 closes — a simulated budget-exceeded Pub/Sub message must trigger the function and disable billing, verified via Cloud Function logs and a `gcloud billing projects describe` check. This satisfies ROADMAP Phase 0 success criterion #3.

**Rationale:** The reference is battle-tested and well-known in the GCP community. Vendoring (vs git submodule) keeps the repo self-contained for portfolio readers. Writing from scratch wastes time on a solved problem with no resume payoff.

### C. Default Region
- **D-07:** Default `GCP_REGION=us-central1`. Documented in `scripts/bootstrap-gcp.env.example` as an override-able env var.
- **D-08:** BigQuery dataset region = `US` (multi-region) — aligns pricing with us-central1 and matches the canonical GCP demo region.
- **D-09:** All Cloud Run Jobs / Workflows / Eventarc triggers pinned to the same region (per Pitfall #13 — region mismatch). Bootstrap script enforces this via a single `$GCP_REGION` variable.
- **D-10:** Add a top-of-script comment: "If you are based in Europe/UK and add live demo links to your portfolio, switch `GCP_REGION` to `europe-west1` before Phase 3 — region cannot be changed in-place after services are created."

**Rationale:** us-central1 is the canonical low-cost full-service GCP region, all required services (Cloud Run Jobs, Workflows, Eventarc, BQ, GCS) are available, and the BQ `US` multi-region pricing is the cheapest option. The override path is documented so a user in Europe can switch with one variable change before any service is deployed.

### D. Local Credentials Handling
- **D-11:** Local development uses Application Default Credentials via `gcloud auth application-default login`. No service-account JSON files in Phase 0.
- **D-12:** Service-account JSON for GitHub Actions is deferred to Phase 6 (PORT-05) — not needed until images are built and pushed.
- **D-13:** Workload Identity Federation is explicitly NOT used in v1 (overkill for a solo portfolio repo).
- **D-14:** `.gitignore` covers `*.json` at repo root, `.env`, `.env.*`, `*.fit` (raw FIT files may contain GPS — privacy hygiene per BOOT-07), `__pycache__`, `.venv`, `.uv-cache`, `*.parquet`, `*.mp4` (large fixture artifacts), and `secrets/`.

**Rationale:** ADC is the standard local-dev path on macOS; the dev experience is `gcloud auth application-default login` once and never think about it again. Deferring SA-JSON until CI exists avoids carrying credential material around before there's a use for it.

### E. Filming Protocol Detail
- **D-15:** `docs/filming-protocol.md` is a concise one-pager with: (i) a 6-item pre-shot checklist, (ii) one labeled side-view ASCII or hand-drawn diagram showing camera placement relative to bottom bracket and a fiducial in frame, (iii) the four hard locks (camera height = BB height ±2 cm, fiducial visible in frame, ≥60fps capture, CFR/constant-frame-rate mandatory, tripod only — no handheld), (iv) one paragraph on lighting (avoid backlit, prefer 5000K LED).
- **D-16:** Protocol includes a "shot-acceptance checklist" the operator runs through the phone preview before pressing record.
- **D-17:** A `docs/filming-protocol-bad-examples.md` is NOT created in Phase 0; capturing bad examples is deferred to Phase 1 when real fixture rides exist.

**Rationale:** This protocol locks the geometry every downstream pose phase depends on (Pitfall #1, Pitfall #8). It needs to be airtight on the four invariants but does not need photography-textbook depth — extra material would dilute the lock-ins.

### F. README JD-Mapping Layout
- **D-18:** README contains a table with one row per JD nice-to-have:

  | JD area | Demonstrated by | Code/doc references | Status |
  |---|---|---|---|
  | CS/Engineering | … | … | placeholder |
  | Computer vision / pose estimation | … | … | placeholder |
  | GCP-based ML workloads | … | … | placeholder |
  | Sport/performance telemetry | … | … | placeholder |

- **D-19:** Phase 0 fills the `Status` column with `placeholder` for every row; later phases overwrite as they ship. Phase 6 (PORT-01) is responsible for the final filled-in version.
- **D-20:** The README also seeds the "What this does NOT do" subsection for Phase 6 (PORT-02) — empty in Phase 0, but the section header exists so later phases can append.

**Rationale:** A table is the hiring-manager-friendly format — skimmable, audit-friendly, and a clear ledger of what the project claims vs proves. Prose hides the mapping; a checklist looks like a TODO list.

### G. CI Scope in Phase 0
- **D-21:** `.github/workflows/ci.yaml` runs `ruff check`, `ruff format --check`, `mypy`, `pytest -q` on push/PR to `main`. Python matrix is single-version (3.12).
- **D-22:** Build + push of container images is deferred to Phase 6 (PORT-05).
- **D-23:** The CI badge URL is included in the README skeleton — even with zero tests passing, the badge being green-after-first-commit is a portfolio signal.
- **D-24:** No pre-commit hooks in Phase 0 — `ruff` + `mypy` in CI is sufficient; pre-commit can be added in Phase 6 if useful.

**Rationale:** A lint+test CI badge live from day 1 is a high-signal portfolio detail at near-zero cost. Build/push requires container images that don't exist yet — coupling those to Phase 0 would block the kill-switch work.

### H. Repo Visibility
- **D-25:** Public GitHub repo from day 1.
- **D-26:** Repo URL is recorded in PROJECT.md once created. Commits are signed with the user's standard GitHub email.
- **D-27:** No secrets or service-account material is ever committed (enforced by `.gitignore` and a one-line documentation note in `CONTRIBUTING.md` skeleton).

**Rationale:** Portfolio value compounds with visibility; a public repo from commit #1 means every commit serves the portfolio narrative. Waiting until "it's good" usually means waiting forever.

### Claude's Discretion
- File and directory naming conventions inside `scripts/`, `infra/`, `docs/`, `lib/` — choose readable names; align with research/STACK.md proposed layout (`pipeline/{pose,fit,features,correlate}/`, `lib/vision/`) where it applies.
- Specific Python package list inside `pyproject.toml` beyond the locked stack (e.g., dev-tools version pins for `pytest-cov`, `pytest-xdist`) — choose modern stable versions.
- ASCII vs simple PNG diagram in filming protocol — ASCII first; upgrade if the user later requests visual polish.
- Whether to add `pyproject.toml` script entrypoints (`vision-bootstrap`, etc.) — add them where they aid discoverability; skip if they only add ceremony.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level locked decisions
- `.planning/PROJECT.md` — core value, scope, key decisions; load-bearing constraints (budget $20/mo, single user, batch-only, no coaching prescriptions)
- `.planning/REQUIREMENTS.md` §Bootstrap — BOOT-01..07 verbatim requirement text
- `.planning/ROADMAP.md` §"Phase 0: Bootstrap & Cost Guardrails" — goal, JD-signal coverage matrix, 5 success criteria
- `.planning/STATE.md` — load-bearing TODOs (≥3 fixture rides, ≥6 FIT edge-cases) carried into Phase 1

### Stack & architecture locks (from research)
- `.planning/research/STACK.md` — Python 3.12, uv, ruff, mypy, pytest pins; "what NOT to use" list (no Terraform for v1, no Cloud Functions for inference, no GPU)
- `.planning/research/ARCHITECTURE.md` — ADR-1 (Cloud Run Jobs not Vertex Endpoint), ADR-2 (alignment as SQL view), ADR-3 (pose in cloud); project layout proposal (`pipeline/`, `lib/vision/`, `infra/`)
- `.planning/research/SUMMARY.md` §"Phase 0: Project Bootstrap & Cost Guardrails" — phase deliverables list and addressed pitfalls

### Pitfall mitigations addressed in Phase 0
- `.planning/research/PITFALLS.md` §Pitfall #4 (GCP cost runaway) — defines the kill switch shape that D-04..06 implement
- `.planning/research/PITFALLS.md` §Pitfall #13 (region mismatch) — drives D-07..10
- `.planning/research/PITFALLS.md` §Pitfall #1 (side-view camera-rig sloppiness) — drives D-15..17
- `.planning/research/PITFALLS.md` §Pitfall #8 (FPS aliasing + VFR) — drives the 60fps + CFR clauses in D-15

### External references (vendored or linked)
- Upstream kill-switch reference: `https://github.com/Cyclenerd/poweroff-google-cloud-cap-billing` — vendored into `infra/kill-switch/` per D-04; credit in `NOTICE`
- GCP Billing budget notifications API — to be cited in the kill-switch README
- Google Cloud "Disable billing on a project" docs — link in the kill-switch README

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — repo is greenfield (no source files, no codebase maps). Phase 0 establishes the assets later phases reuse (toolchain, scripts/, infra/, docs/).

### Established Patterns
- The patterns this phase establishes (single `GCP_REGION` env var, vendored upstream code with `NOTICE`, gcloud setup script, single-version CI matrix) become the established patterns later phases must follow.
- File layout target (informed by `.planning/research/ARCHITECTURE.md`):
  ```
  scripts/                  # bootstrap and operational scripts (D-01..03)
  infra/kill-switch/        # vendored Cyclenerd kill switch (D-04..06)
  docs/filming-protocol.md  # one-pager protocol (D-15..17)
  pyproject.toml + uv.lock  # toolchain (BOOT-01)
  .github/workflows/ci.yaml # lint+test CI (D-21..24)
  .gitignore                # privacy hygiene (BOOT-07, D-14)
  README.md                 # JD-mapping table (D-18..20)
  NOTICE                    # upstream credit (D-04)
  CONTRIBUTING.md           # one-line "no secrets" note (D-27)
  ```

### Integration Points
- This phase has zero runtime integration points (no compute, no data flow). Integration begins in Phase 1 (local code) and continues into Phase 3 (GCS/BQ).
- The one cross-cutting concern: `GCP_REGION` env var must be the single source of truth for every subsequent GCP resource creation, in every later phase.

</code_context>

<specifics>
## Specific Ideas

- Kill-switch implementation should mirror the reference's Pub/Sub-message-shape contract so that a real GCP Billing budget notification is byte-compatible with our test payload.
- README JD-mapping table should sit ABOVE the architecture diagram, not below — hiring manager reads top-down.
- Mention in the kill-switch README that disabling billing also stops all running services after a short delay, so this is a one-way "last resort" door — explicitly call out that the user must re-enable billing manually to recover.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-environment GCP projects (dev/staging/prod)** — out of scope for a solo single-user portfolio; capture only if the project grows past v1.
- **Pre-commit hooks (ruff/mypy auto-run on git commit)** — defer to Phase 6 if there's appetite; CI alone is sufficient now.
- **Cost dashboard screenshot in README** — Phase 6 deliverable (PORT-06 area).
- **`docs/filming-protocol-bad-examples.md` (annotated bad-shot examples)** — defer to Phase 1 when real fixture rides exist; no real footage yet to annotate.
- **PNG or SVG diagram of the filming protocol** — ASCII first; upgrade if the user later asks for visual polish.
- **`pyproject.toml` script entrypoints** — add only if they aid discoverability when actual code lands; skip the ceremony otherwise.
- **GitHub repository templates (issue templates, PR template)** — defer to Phase 6; not part of the bootstrap critical path.

</deferred>

---

*Phase: 0-Bootstrap & Cost Guardrails*
*Context gathered: 2026-05-20*
