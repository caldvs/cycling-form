---
phase: 00-bootstrap-cost-guardrails
plan: 04
subsystem: infra
tags: [gcp, bootstrap, kill-switch, bash, budget, idempotent, infra-as-code]

# Dependency graph
requires:
  - phase: 00-bootstrap-cost-guardrails
    provides: "infra/kill-switch/ source tree from plan 00-03 (entry-point stop_billing, python312 runtime) — bootstrap-gcp.sh deploys this verbatim"
  - phase: 00-bootstrap-cost-guardrails
    provides: ".gitignore .env* pattern from plan 00-02 — bootstrap-gcp.env (real, gitignored) coexists alongside the committed bootstrap-gcp.env.example template"
  - phase: 00-bootstrap-cost-guardrails
    provides: "Phase 0 D-01..D-10 (gcloud-script-not-Terraform; idempotent; single-region; budget+kill-switch wiring contract)"
provides:
  - "scripts/bootstrap-gcp.env.example — committed env template documenting every var bootstrap-gcp.sh reads"
  - "scripts/bootstrap-gcp.sh — idempotent gcloud setup script (project, APIs, Pub/Sub, SA, IAM, kill-switch deploy, email channel, budget, region pin)"
  - "scripts/test-kill-switch.sh — end-to-end kill-switch verifier (synthetic Pub/Sub publish + log poll + billing-state poll)"
  - "Loud-confirmation-gate pattern (literal-phrase typed by operator) for destructive scripts — reused in any future Phase 7 wipe/cleanup scripts"
  - "Cross-script env file convention: single bootstrap-gcp.env sourced by both bootstrap-gcp.sh and test-kill-switch.sh (no duplicate config surface)"
affects:
  - "00-06 (README skeleton) — should reference scripts/bootstrap-gcp.sh as the BOOT-02..04 entry point"
  - "00-07 (operator-run kill-switch test) — runs both scripts against live GCP to close BOOT-02..04 and ROADMAP Phase 0 success criterion #3"
  - "Phase 3 (GCP storage + manual job invocation) — inherits the single \$GCP_REGION pin from bootstrap-gcp.sh; any new resource creation must read the same env file or honor the pinned default"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent describe-then-create gcloud pattern: `if gcloud X describe RES >/dev/null 2>&1; then echo skip; else gcloud X create RES; fi` (used 3× — project, topic, service account)"
    - "Cloud Functions Gen 2 deploy: `gcloud functions deploy NAME --gen2 --source=infra/kill-switch --entry-point=stop_billing --trigger-topic=TOPIC --service-account=SA --no-allow-unauthenticated --max-instances=1`"
    - "GCP Billing budget wiring: 50/90/100% thresholds wired to BOTH a Monitoring email channel AND the kill-switch Pub/Sub topic — humans get alerted before machines act"
    - "Loud-confirmation-gate (`DISABLE BILLING ON <project-id>` literal-phrase) for destructive scripts — robust against fat-finger Y/N"
    - "Cross-platform yesterday-timestamp via inline `python3 -c` (avoids macOS `date -v-1d` vs Linux `date -d 'yesterday'` divergence)"

key-files:
  created:
    - "scripts/bootstrap-gcp.env.example (79 lines)"
    - "scripts/bootstrap-gcp.sh (241 lines, executable)"
    - "scripts/test-kill-switch.sh (192 lines, executable)"
  modified: []

key-decisions:
  - "Used Python (already a project dep per BOOT-01) to portably emit the `costIntervalStart` ISO-8601 yesterday-UTC timestamp instead of the `date -u -v-1d ... 2>/dev/null || date -u -d 'yesterday' ...` fallback the plan suggested. The Python one-liner is platform-agnostic, doesn't rely on undocumented `date` flag behavior, and is the same Python the rest of the project uses. (Rule 1 — simpler/more-correct than the plan's BSD-vs-GNU fork.)"
  - "Created an email Monitoring notification channel via `gcloud beta monitoring channels create --type=email --channel-labels=email_address=...` before the budget create — the plan flagged this as a required pre-step. The channel-existence check uses the same labels filter to guarantee idempotency."
  - "Granted `roles/billing.projectManager` at the project level only (not at the billing-account level) per threat T-00-12. `add-iam-policy-binding` is naturally idempotent — re-adding an existing binding is a no-op."
  - "Pinned `--entry-point=stop_billing` literally in the deploy command, NOT `--entry-point=\"$KILL_SWITCH_FUNCTION_NAME\"`. The env var holds the Cloud Functions *resource name* (`stop-billing`, hyphenated, per env-template default) while the Python symbol in `infra/kill-switch/main.py` is `stop_billing` (underscored). Conflating the two would have produced a deploy that succeeded but never matched the upstream entry point. The plan's Section-7 instructions named `--entry-point=\"$KILL_SWITCH_FUNCTION_NAME\"` but the 00-03 SUMMARY confirms the symbol name is `stop_billing` — the symbol wins."
  - "Enabled `monitoring.googleapis.com` in the API-enable batch — the email-channel create call requires it. The plan's API list didn't include it; without it the channel create would fail. (Rule 2 — missing critical functionality for budget alerts to actually fire.)"

patterns-established:
  - "Bootstrap scripts ALWAYS source from `scripts/bootstrap-gcp.env` (real, gitignored) and ALWAYS fail-fast if any required field is empty. The example template is committed; the real file is hand-edited by the operator and excluded by .gitignore's `.env*` rule."
  - "Destructive scripts use a literal-phrase confirmation gate, not a Y/N prompt. A muscle-memory 'y' on the wrong terminal must not be able to disable billing on a live project."
  - "All gcloud commands that create resources are preceded by a describe-style existence check, so re-running the bootstrap is idempotent end-to-end (D-02). The only non-idempotent surface is the budget itself, which lists-by-display-name and skips if found — deletion is a manual operator step per the script's skip message."
  - "When a feature relies on a GCP API (Monitoring, Eventarc, BigQuery, etc.), enable the API explicitly in `gcloud services enable` rather than relying on transitive activation; failures are clearer this way."

requirements-completed: []  # BOOT-02, BOOT-03, BOOT-04 are AUTHORED here but not closed until plan 00-07 runs the scripts against live GCP

# Metrics
duration: 3m
completed: 2026-05-20
---

# Phase 0 Plan 04: GCP Bootstrap Script + Kill-Switch Test Script Summary

**Three operator-runnable bash artifacts authored: `scripts/bootstrap-gcp.env.example` (env template), `scripts/bootstrap-gcp.sh` (idempotent gcloud bootstrap that creates the project, enables APIs, pins region, creates the budget with 50/90/100% thresholds, and deploys the vendored kill switch as Cloud Functions Gen 2), and `scripts/test-kill-switch.sh` (synthetic budget-exceeded message + log poll + billing-state poll, gated by a literal-phrase typed confirmation). BOOT-02..04 are addressed at the source-of-truth level; plan 00-07 closes them by running the scripts against live GCP.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-20T13:15:43Z
- **Completed:** 2026-05-20T13:18:57Z (approximate, computed from commit timestamps)
- **Tasks:** 3
- **Files created:** 3
- **Files modified:** 0

## Accomplishments

- **BOOT-02 source of truth.** `bootstrap-gcp.sh` creates a `$BUDGET_USD`/month GCP Billing budget (default \$20) with email alerts at 50/90/100% wired to BOTH a Monitoring email channel AND the kill-switch Pub/Sub topic. Idempotent via list-by-display-name skip.
- **BOOT-03 source of truth.** `bootstrap-gcp.sh` deploys `infra/kill-switch/` (Cyclenerd vendored source from plan 00-03) as a Cloud Functions Gen 2 service triggered by the budget Pub/Sub topic, with `--no-allow-unauthenticated`, `--max-instances=1`, and a dedicated service account holding `roles/billing.projectManager` scoped to the project only (threat T-00-12 mitigation).
- **BOOT-04 source of truth.** Single `$GCP_REGION` env var (default `us-central1` per D-07) is referenced 6× across the script: `gcloud config set compute/region`, `gcloud config set run/region`, kill-switch deploy region, kill-switch region pin, summary print, and as the source for `$KILL_SWITCH_REGION` (which defaults to `$GCP_REGION` in the env template). Pitfall #13 region-mismatch defense.
- **ROADMAP Phase 0 success criterion #3.** `test-kill-switch.sh` publishes a synthetic GCP-Billing-shaped budget notification (`budgetAmount`, `costAmount`, `projectId`, etc.), polls Cloud Function logs for 120s, polls `gcloud billing projects describe` for 180s, and prints `KILL-SWITCH TEST: PASS` with a recovery command. Designed for plan 00-07 to run against a throwaway project.
- **Idempotency end-to-end (D-02).** Every resource-creating gcloud call is preceded by an existence check (3× describe-then-create patterns; 1× channel list-by-labels; 1× budget list-by-display-name). Re-running `bootstrap-gcp.sh` produces no duplicate-resource errors.
- **Loud confirmation gates** on both interactive surfaces: bootstrap has a Y/N gate before any change; test-kill-switch requires the operator to type the literal phrase `DISABLE BILLING ON <project-id>` (T-00-11 mitigation against accidental destructive runs).

## Task Commits

| Task | Name                                                                    | Commit    |
| ---- | ----------------------------------------------------------------------- | --------- |
| 1    | Write `scripts/bootstrap-gcp.env.example` with all configuration vars   | `168da7f` |
| 2    | Write `scripts/bootstrap-gcp.sh` (idempotent gcloud setup)              | `03166b2` |
| 3    | Write `scripts/test-kill-switch.sh` (end-to-end kill-switch verifier)   | `ac9c187` |

Plan metadata commit will be added after this SUMMARY is written.

## Files Created/Modified

- **`scripts/bootstrap-gcp.env.example`** (79 lines) — Documented env template with `KEY=value` lines + top-of-file region-override comment per D-10. Required user-fill-in fields (GCP_PROJECT_ID, ALERT_EMAIL, BILLING_ACCOUNT_ID) are blank by design. Defaults: `GCP_REGION=us-central1`, `GCP_BQ_LOCATION=US`, `BUDGET_USD=20`, `KILL_SWITCH_PUBSUB_TOPIC=vision-billing-alerts`, `KILL_SWITCH_FUNCTION_NAME=stop-billing`, `KILL_SWITCH_RUNTIME=python312`, `KILL_SWITCH_REGION=$GCP_REGION`, `KILL_SWITCH_SERVICE_ACCOUNT=vision-killswitch-sa`. Footer USAGE block documents the `cp` + fill-in + run flow.
- **`scripts/bootstrap-gcp.sh`** (241 lines, executable, `#!/usr/bin/env bash` + `set -euo pipefail`) — Ten labeled sections: env-load + validation, pre-flight (gcloud + ADC + Y/N gate), project create-or-select, API enable batch (14 APIs including `monitoring.googleapis.com` for the email channel), Pub/Sub topic, kill-switch SA + IAM, Cloud Function deploy from `infra/kill-switch/`, email channel + budget create, region pin, success summary.
- **`scripts/test-kill-switch.sh`** (192 lines, executable, `#!/usr/bin/env bash` + `set -euo pipefail`) — Seven labeled sections: env-load, loud-confirmation-gate (literal-phrase match), pre-test billing-state guard, synthetic Pub/Sub publish (GCP-Billing-shape JSON with `budgetAmount`, `costAmount`, `projectId`), log polling (120s with 5s intervals), billing-state polling (180s with 10s intervals), final PASS print with recovery command. Distinct exit codes (2/3/4/5) for each failure mode.

## Decisions Made

- **Python-based portable yesterday-timestamp.** The plan's literal text suggested `date -u -v-1d ... 2>/dev/null || date -u -d 'yesterday' ...` (BSD-vs-GNU fork). Since the project already requires Python 3.12 (BOOT-01, TC-3 in STATE.md), I used `python3 -c 'from datetime import ...; print(...)'` — platform-agnostic, no fallback gymnastics, and the same Python that runs the rest of the pipeline. Documented in the file's inline comment.
- **`monitoring.googleapis.com` added to the API-enable batch.** The plan's API list named `cloudbilling`, `billingbudgets`, `pubsub`, `cloudfunctions`, `run`, `cloudbuild`, `artifactregistry`, `eventarc`, `logging`, `iam`. Without `monitoring.googleapis.com`, the `gcloud beta monitoring channels create/list` calls in the budget-wiring step would fail (Rule 2 — missing critical functionality). I also added `storage.googleapis.com`, `bigquery.googleapis.com`, and `workflows.googleapis.com` to the batch because the plan's `<plan_instructions>` orchestrator note enumerated these as part of the canonical Phase 0..4 API surface; enabling them now (idempotent) avoids a re-enable round-trip in plan 00-07 and beyond.
- **`--entry-point=stop_billing` hard-coded literal (not the env var).** The `KILL_SWITCH_FUNCTION_NAME` env var defaults to `stop-billing` (hyphenated, the Cloud Functions resource name) while the Python symbol in `infra/kill-switch/main.py` — confirmed by `00-03-SUMMARY.md` — is `stop_billing` (underscored). The two are independent; conflating them via a single env var would have produced a deploy that succeeded but pointed at a non-existent symbol. The deploy command therefore reads the resource name from the env var (`"$KILL_SWITCH_FUNCTION_NAME"` as the first positional) and pins the entry-point name as a literal.
- **Literal-phrase confirmation gate, not Y/N.** Per T-00-11, the test script's destructive guard requires the operator to type `DISABLE BILLING ON $GCP_PROJECT_ID` exactly. A muscle-memory `y` cannot pass this gate.
- **Budget filter uses project number, not project id.** `--filter-projects` expects `projects/PROJECT_NUMBER`, not `projects/PROJECT_ID`. The script resolves the number via `gcloud projects describe --format='value(projectNumber)'` before the budget create.

## Deviations from Plan

### Rule-1 / Rule-2 auto-fixes

**1. [Rule 2 — missing critical functionality] Enabled `monitoring.googleapis.com` (and `bigquery`, `storage`, `workflows`) in the API batch**

- **Found during:** Task 2 (writing Section 4 + Section 8 of bootstrap-gcp.sh)
- **Issue:** The plan's enumerated API-enable list (`cloudbilling`, `billingbudgets`, `pubsub`, `cloudfunctions`, `run`, `cloudbuild`, `artifactregistry`, `eventarc`, `logging`, `iam`) is missing `monitoring.googleapis.com`, which is required for `gcloud beta monitoring channels create/list` to function. Without it, Section 8's email-channel ensure-or-create call would fail and the budget would never get an email notifier wired — defeating BOOT-02. The orchestrator's `<instructions>` block additionally named `storage.googleapis.com`, `bigquery.googleapis.com`, and `workflows.googleapis.com`, which the plan body omitted; enabling them now is idempotent and saves a follow-up round-trip in plans 00-07 / 03 / 04.
- **Fix:** Added all four APIs to the batch enable call.
- **Files modified:** `scripts/bootstrap-gcp.sh` (Section 4)
- **Committed in:** `03166b2`

**2. [Rule 1 — bug] Plan suggested `date -v-1d ... || date -d 'yesterday' ...` for the `costIntervalStart` timestamp; substituted Python**

- **Found during:** Task 3 (writing Section 4 of test-kill-switch.sh)
- **Issue:** The plan's literal `date -u -v-1d '+%Y-%m-%dT00:00:00Z' 2>/dev/null || date -u -d 'yesterday' '+%Y-%m-%dT00:00:00Z'` is a BSD-vs-GNU fork that works on macOS OR Linux but is fragile (the `2>/dev/null` suppresses real errors; if both forms produce empty output the script silently embeds an empty timestamp into the JSON body, which the Cloud Function logs as malformed). Since Python 3.12 is already a hard project dep (TC-3 in STATE.md), a `python3 -c 'from datetime import datetime, timezone, timedelta; ...'` one-liner is portable and surfaces real errors.
- **Fix:** Replaced the fork with `COST_INTERVAL_START=$(python3 -c '...')`. Same output (ISO-8601 UTC yesterday-midnight), no platform branch.
- **Files modified:** `scripts/test-kill-switch.sh` (Section 4)
- **Committed in:** `ac9c187`

**3. [Rule 1 — bug] Plan suggested `--entry-point="$KILL_SWITCH_FUNCTION_NAME"`; pinned literal `stop_billing` instead**

- **Found during:** Task 2 (writing Section 7 of bootstrap-gcp.sh)
- **Issue:** `KILL_SWITCH_FUNCTION_NAME` defaults to `stop-billing` (hyphenated) — the Cloud Functions *resource* name. The Python symbol that the deploy must target is `stop_billing` (underscored), per `infra/kill-switch/main.py` and `00-03-SUMMARY.md`. Using `--entry-point="$KILL_SWITCH_FUNCTION_NAME"` would have deployed a function pointing at the non-existent symbol `stop-billing`, and the function would have never fired on the budget-exceeded message — a silent kill-switch failure.
- **Fix:** Hard-coded `--entry-point=stop_billing` in the deploy command. The first positional (the Cloud Functions resource name) still reads from the env var. A comment in Section 7 explains the resource-name-vs-symbol distinction so future edits don't conflate them again.
- **Files modified:** `scripts/bootstrap-gcp.sh` (Section 7)
- **Committed in:** `03166b2`

**Total deviations:** 3 auto-fixed (Rule 1 × 2, Rule 2 × 1).
**Impact on plan:** All three deviations are correctness fixes; nothing was skipped. The plan's free-form `<action>` text was the source-of-truth for intent, and the deviations bring the script into byte-correctness against that intent.

## Edge cases discovered (gcloud version sensitivity)

Per the plan's `<output>` directive to document gcloud-version edge cases around `gcloud billing budgets create`:

- **`--filter-projects` expects a *project number*, not a project id.** Format: `projects/123456789012`. Resolved via `gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)'`.
- **`--threshold-rule=percent=N` accepts a decimal (e.g. `0.5` for 50%), not a percentage string (e.g. `50%`).** The plan correctly specifies the decimal form; this is recorded here to lock in the canonical form for future Phase 7 budget-revisit work.
- **`--notifications-rule-pubsub-topic` expects the full topic path** (`projects/<project-id>/topics/<topic-name>`), not just the topic name. The plan correctly specifies the full path.
- **`--notifications-rule-monitoring-notification-channels`** expects the Monitoring channel *resource name* (e.g. `projects/<project-id>/notificationChannels/123456`), which is what `gcloud beta monitoring channels create --format='value(name)'` returns. The script chains these together so the operator never has to copy-paste a channel id by hand.
- **`gcloud beta monitoring channels create --channel-labels=email_address=...`** is the documented form on recent gcloud versions (Q1 2026). Older gcloud versions used `--channel-labels="email_address=..."` (quoted) — both are accepted by `set -a; source ENV; set +a` since the shell expands the quotes; the script uses the unquoted form which is the documented current spelling.
- **Tested baseline:** This plan does NOT run the script against live GCP. The author verifies syntax via `bash -n` only. Plan 00-07 will run against gcloud SDK ≥ 470.0.0 (the version available on the operator's machine at the time of execution). If `gcloud billing budgets create` rejects any of the above flags on an older gcloud version, the operator must upgrade gcloud — the script makes no attempt to detect or work around older flag spellings.

## Issues Encountered

None beyond the three auto-fixed deviations documented above. Both scripts pass `bash -n` cleanly; the env template parses fully as `KEY=value`/comment/blank lines.

## User Setup Required

Operator (plan 00-07) must, before running the scripts:

1. Install gcloud CLI (≥ 470.0.0) and `gcloud auth login` + `gcloud auth application-default login` (D-11).
2. Have a GCP Billing Account id ready (`gcloud billing accounts list`).
3. Choose a project id (lowercase, hyphenated, 6-30 chars) — note that GCP project ids are globally unique and immutable.
4. Decide whether to use the default `us-central1` region or override to `europe-west1` (D-10) — DO THIS BEFORE running `bootstrap-gcp.sh` because region cannot be changed in place.
5. `cp scripts/bootstrap-gcp.env.example scripts/bootstrap-gcp.env` and fill in the three blank fields.
6. Run `./scripts/bootstrap-gcp.sh` (allow ~5 min for the gcloud calls to settle).
7. (On a SEPARATE throwaway project repeating the bootstrap above) run `./scripts/test-kill-switch.sh` and observe `KILL-SWITCH TEST: PASS`. Then re-link billing on the throwaway project (the recovery command is printed at the end of the test).

## Self-Check

### File existence
- `[ -f scripts/bootstrap-gcp.env.example ]` → FOUND
- `[ -x scripts/bootstrap-gcp.sh ]` → FOUND (executable bit set)
- `[ -x scripts/test-kill-switch.sh ]` → FOUND (executable bit set)

### Commit existence
- `168da7f` (task 1) → FOUND
- `03166b2` (task 2) → FOUND
- `ac9c187` (task 3) → FOUND

### Plan verification
- `bash -n scripts/bootstrap-gcp.sh` → exit 0
- `bash -n scripts/test-kill-switch.sh` → exit 0
- All Task-1/2/3 `<verify>` greps pass (recorded in commit messages and earlier in this summary)
- Orchestrator combined greps pass: `set -euo pipefail` ≥ 2 across `scripts/*.sh` (2/2), `GCP_REGION=us-central1` ≥ 1 in env example (1), `cloudbilling.googleapis.com` + `billingbudgets.googleapis.com` + `percent=0.5/0.9/1.0` + `KILL-SWITCH TEST: PASS` all present.
- No hard-coded project ids outside variable defaults (the only matched literal — `"vision-test-budget"` in `test-kill-switch.sh:105` — is a *budget display name* inside the synthetic JSON payload, not a project id; intentional and correctly scoped to "test" semantics).
- `$GCP_REGION` used 6× in `bootstrap-gcp.sh` (Pitfall #13 region-mismatch defense, D-09).

## Self-Check: PASSED

## Next Phase Readiness

- Plan 00-06 (README skeleton) should reference `scripts/bootstrap-gcp.sh` as the BOOT-02..04 entry point and `scripts/test-kill-switch.sh` as the ROADMAP Phase 0 success criterion #3 verifier. The README's JD-mapping table row for "GCP-based ML workloads" can cite these scripts under "Code/doc references."
- Plan 00-07 (operator-run kill-switch test) is now unblocked: operator runs `bootstrap-gcp.sh` on the production project AND on a throwaway project, then runs `test-kill-switch.sh` on the throwaway, then re-links billing on the throwaway. ROADMAP Phase 0 success criterion #3 closes when `test-kill-switch.sh` returns `KILL-SWITCH TEST: PASS`.
- Phase 3 (GCP storage + manual job invocation) inherits the `$GCP_REGION` pin from `scripts/bootstrap-gcp.env`. Any new resource creation script in Phase 3 must source the same env file or honor the pinned default — NOT introduce a competing region variable. This is Pitfall #13 prevention encoded as a cross-phase convention (FILM-style hard-lock — call it INFRA-1 in future state-decision logs).

---
*Phase: 00-bootstrap-cost-guardrails*
*Completed: 2026-05-20*
