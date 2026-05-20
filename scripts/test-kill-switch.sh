#!/usr/bin/env bash
# test-kill-switch.sh — end-to-end test of the billing kill switch.
#
# DESTRUCTIVE — disables billing on the configured project.
# Run ONLY on a throwaway test project.
#
# THIS SCRIPT DISABLES BILLING ON THE TARGET PROJECT.
# RUN ONLY AGAINST A DISPOSABLE THROWAWAY PROJECT (D-06).
#
# Procedure:
#   1. Confirm the operator understands the warning (must type a literal phrase).
#   2. Publish a synthetic budget-exceeded message to KILL_SWITCH_PUBSUB_TOPIC.
#   3. Poll Cloud Function logs for evidence the function ran (timeout 120s).
#   4. Poll billing state via 'gcloud billing projects describe' until
#      billingEnabled=False (timeout 180s).
#   5. Print KILL-SWITCH TEST: PASS or KILL-SWITCH TEST: FAIL.
#
# Exit codes:
#   0 — PASS
#   1 — generic error (set -e propagated)
#   2 — operator aborted at confirmation gate
#   3 — billing was already disabled before the test (no meaningful test)
#   4 — Cloud Function log marker not seen within 120s
#   5 — billing still enabled after 180s post-publish
set -euo pipefail

# ----------------------------------------------------------------------
# Section 1 — Load env (same pattern as bootstrap-gcp.sh)
# ----------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/bootstrap-gcp.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy bootstrap-gcp.env.example and fill it in." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

REQUIRED_VARS=(
  GCP_PROJECT_ID
  KILL_SWITCH_PUBSUB_TOPIC
  KILL_SWITCH_FUNCTION_NAME
  KILL_SWITCH_REGION
  BUDGET_USD
)
for v in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: required env var '$v' is empty in $ENV_FILE." >&2
    exit 1
  fi
done

# ----------------------------------------------------------------------
# Section 2 — Loud confirmation gate (D-06 + kill-switch README one-way-door)
# ----------------------------------------------------------------------
echo ""
echo "############################################################"
echo "# WARNING: THIS WILL DISABLE BILLING ON $GCP_PROJECT_ID."
echo "# RUN ONLY ON A THROWAWAY TEST PROJECT (D-06)."
echo "# DISABLING BILLING STOPS ALL SERVICES AFTER A SHORT DELAY."
echo "############################################################"
echo ""
EXPECTED_PHRASE="DISABLE BILLING ON $GCP_PROJECT_ID"
echo "Type the following phrase EXACTLY to proceed:"
echo "  $EXPECTED_PHRASE"
echo ""
read -r OPERATOR_INPUT
if [[ "$OPERATOR_INPUT" != "$EXPECTED_PHRASE" ]]; then
  echo "Confirmation phrase did not match. Aborting." >&2
  exit 2
fi

# ----------------------------------------------------------------------
# Section 3 — Capture the pre-test state
# ----------------------------------------------------------------------
PRE_STATE=$(gcloud billing projects describe "$GCP_PROJECT_ID" \
  --format='value(billingEnabled)')

if [[ "$PRE_STATE" != "True" ]]; then
  echo "Billing is already disabled on $GCP_PROJECT_ID — cannot run a meaningful test." >&2
  exit 3
fi
echo "Pre-test billing state on $GCP_PROJECT_ID: enabled."

# ----------------------------------------------------------------------
# Section 4 — Publish the synthetic budget-exceeded message
# ----------------------------------------------------------------------
# Shape mirrors GCP Billing's budget-notification JSON:
#   https://cloud.google.com/billing/docs/how-to/notify
# The vendored main.py reads `costAmount`, `budgetAmount`, and optionally
# `projectId` from the message body. We publish projectId both in the
# message body (for the function) and as a Pub/Sub attribute (defensively,
# in case any future adaptation reads attributes instead).
#
# Use python (already a project dep) to portably emit an ISO-8601 UTC
# timestamp for yesterday — avoids the macOS/Linux `date` arg incompatibility.
COST_INTERVAL_START=$(python3 -c 'from datetime import datetime, timezone, timedelta; print((datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"))')

MESSAGE_BODY=$(cat <<EOF
{
  "budgetDisplayName": "vision-test-budget",
  "alertThresholdExceeded": 1.0,
  "costAmount": $(awk "BEGIN { print ${BUDGET_USD} + 0.01 }"),
  "costIntervalStart": "${COST_INTERVAL_START}",
  "budgetAmount": ${BUDGET_USD}.00,
  "budgetAmountType": "SPECIFIED_AMOUNT",
  "currencyCode": "USD",
  "projectId": "${GCP_PROJECT_ID}"
}
EOF
)

echo "Publishing synthetic budget-exceeded message to topic '$KILL_SWITCH_PUBSUB_TOPIC'..."
gcloud pubsub topics publish "$KILL_SWITCH_PUBSUB_TOPIC" \
  --project="$GCP_PROJECT_ID" \
  --message="$MESSAGE_BODY" \
  --attribute="projectId=$GCP_PROJECT_ID,budgetId=test-budget"

# ----------------------------------------------------------------------
# Section 5 — Poll Cloud Function logs for evidence the function ran (120s)
# ----------------------------------------------------------------------
START_TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
DEADLINE=$(($(date +%s) + 120))
LOG_FOUND=0

while [[ $(date +%s) -lt $DEADLINE ]]; do
  if gcloud functions logs read "$KILL_SWITCH_FUNCTION_NAME" \
        --gen2 \
        --region="$KILL_SWITCH_REGION" \
        --project="$GCP_PROJECT_ID" \
        --limit=20 \
        --format='value(log)' \
        --start-time="$START_TS" 2>/dev/null \
        | grep -qiE 'billing disabled|updatebillinginfo|stop_billing'; then
    echo "Cloud Function logged the disable-billing action."
    LOG_FOUND=1
    break
  fi
  sleep 5
done

if [[ "$LOG_FOUND" -ne 1 ]]; then
  echo "Cloud Function log marker not seen within 120s. Last 50 log lines:" >&2
  gcloud functions logs read "$KILL_SWITCH_FUNCTION_NAME" \
    --gen2 \
    --region="$KILL_SWITCH_REGION" \
    --project="$GCP_PROJECT_ID" \
    --limit=50 2>&1 | tail -n 50 >&2 || true
  echo "KILL-SWITCH TEST: FAIL (log marker not found)"
  exit 4
fi

# ----------------------------------------------------------------------
# Section 6 — Poll billing state until disabled (180s)
# ----------------------------------------------------------------------
DEADLINE=$(($(date +%s) + 180))
BILLING_DISABLED=0

while [[ $(date +%s) -lt $DEADLINE ]]; do
  POST_STATE=$(gcloud billing projects describe "$GCP_PROJECT_ID" \
    --format='value(billingEnabled)')
  if [[ "$POST_STATE" == "False" ]]; then
    echo "Billing disabled on $GCP_PROJECT_ID."
    BILLING_DISABLED=1
    break
  fi
  sleep 10
done

if [[ "$BILLING_DISABLED" -ne 1 ]]; then
  echo "Kill switch did not disable billing within 180s. Check Cloud Function logs and IAM permissions." >&2
  echo "KILL-SWITCH TEST: FAIL (billing still enabled)"
  exit 5
fi

# ----------------------------------------------------------------------
# Section 7 — Final PASS
# ----------------------------------------------------------------------
echo ""
echo "============================================================"
echo "KILL-SWITCH TEST: PASS"
echo "============================================================"
echo "Project:  $GCP_PROJECT_ID"
echo "Topic:    $KILL_SWITCH_PUBSUB_TOPIC"
echo "Function: $KILL_SWITCH_FUNCTION_NAME (region $KILL_SWITCH_REGION)"
echo ""
echo "To recover: gcloud billing projects link $GCP_PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>"
echo "============================================================"
