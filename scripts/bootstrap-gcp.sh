#!/usr/bin/env bash
# bootstrap-gcp.sh — idempotent GCP setup for the Vision project.
#
# Satisfies BOOT-02 (budget + alerts), BOOT-03 (kill switch deployed),
# BOOT-04 (single region pin). Operator runs once after editing
# scripts/bootstrap-gcp.env. Re-running is safe (idempotent per D-02).
#
# What this script does, in order:
#   1. Load + validate scripts/bootstrap-gcp.env
#   2. Pre-flight: gcloud on PATH, ADC authenticated, operator confirms
#   3. Create (or select) the GCP project; link billing
#   4. Enable required APIs in a single batch call
#   5. Create the Pub/Sub topic for budget alerts (idempotent)
#   6. Create the kill-switch service account; grant
#      roles/billing.projectManager (least-privilege for updateBillingInfo)
#   7. Deploy the Cloud Function (Gen 2) from infra/kill-switch/
#   8. Ensure an email Monitoring notification channel exists;
#      create the budget with 50/90/100% thresholds wired to both
#      the email channel and the kill-switch Pub/Sub topic
#   9. Pin compute/region and run/region to $GCP_REGION (D-09)
#  10. Print a success summary + next-step pointer
#
# Run from any directory; the script resolves its own location.
set -euo pipefail

# ----------------------------------------------------------------------
# Section 1 — Load env
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
  GCP_REGION
  GCP_BQ_LOCATION
  BUDGET_USD
  BUDGET_DISPLAY_NAME
  ALERT_EMAIL
  BILLING_ACCOUNT_ID
  KILL_SWITCH_PUBSUB_TOPIC
  KILL_SWITCH_FUNCTION_NAME
  KILL_SWITCH_RUNTIME
  KILL_SWITCH_REGION
  KILL_SWITCH_SERVICE_ACCOUNT
)
for v in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: required env var '$v' is empty in $ENV_FILE." >&2
    exit 1
  fi
done

# ----------------------------------------------------------------------
# Section 2 — Pre-flight checks
# ----------------------------------------------------------------------
command -v gcloud >/dev/null || {
  echo "ERROR: gcloud not on PATH. Install the Google Cloud SDK first." >&2
  exit 1
}

# Per D-11, ADC is the auth path for local development.
gcloud auth print-identity-token >/dev/null 2>&1 || {
  echo "ERROR: not authenticated. Run 'gcloud auth login' and 'gcloud auth application-default login' first." >&2
  exit 1
}

echo "About to bootstrap GCP project '$GCP_PROJECT_ID' in region '$GCP_REGION' with \$$BUDGET_USD/month budget. Continue? [y/N]"
read -r REPLY
[[ "$REPLY" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

# ----------------------------------------------------------------------
# Section 3 — Create or select project (idempotent)
# ----------------------------------------------------------------------
if gcloud projects describe "$GCP_PROJECT_ID" >/dev/null 2>&1; then
  echo "Project $GCP_PROJECT_ID already exists, skipping create."
else
  gcloud projects create "$GCP_PROJECT_ID" --name="Vision (Cycling Form Analyzer)"
fi

gcloud billing projects link "$GCP_PROJECT_ID" \
  --billing-account="$BILLING_ACCOUNT_ID"

gcloud config set project "$GCP_PROJECT_ID"

# ----------------------------------------------------------------------
# Section 4 — Enable required APIs (idempotent — services enable is a no-op
# if already enabled)
# ----------------------------------------------------------------------
# We enable billingbudgets early so 'gcloud billing budgets' works.
# cloudbilling-budget.googleapis.com may not exist as a separate service in
# all gcloud versions — both names listed for forward compatibility.
gcloud services enable \
  cloudbilling.googleapis.com \
  billingbudgets.googleapis.com \
  pubsub.googleapis.com \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  eventarc.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  workflows.googleapis.com \
  --project="$GCP_PROJECT_ID"

# ----------------------------------------------------------------------
# Section 5 — Create Pub/Sub topic (idempotent)
# ----------------------------------------------------------------------
if ! gcloud pubsub topics describe "$KILL_SWITCH_PUBSUB_TOPIC" \
      --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  gcloud pubsub topics create "$KILL_SWITCH_PUBSUB_TOPIC" \
    --project="$GCP_PROJECT_ID"
else
  echo "Topic $KILL_SWITCH_PUBSUB_TOPIC already exists, skipping."
fi

# ----------------------------------------------------------------------
# Section 6 — Kill-switch service account + IAM (idempotent)
# ----------------------------------------------------------------------
SA_EMAIL="${KILL_SWITCH_SERVICE_ACCOUNT}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" \
      --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$KILL_SWITCH_SERVICE_ACCOUNT" \
    --display-name="Vision billing kill-switch" \
    --project="$GCP_PROJECT_ID"
else
  echo "Service account $SA_EMAIL already exists, skipping."
fi

# roles/billing.projectManager grants updateBillingInfo at the project level.
# add-iam-policy-binding is naturally idempotent (re-adding is a no-op).
# Scope is the project — NOT the billing account — per threat T-00-12.
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/billing.projectManager" \
  --condition=None

# ----------------------------------------------------------------------
# Section 7 — Deploy the Cloud Function (Gen 2) from infra/kill-switch/
# ----------------------------------------------------------------------
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# NOTE: --entry-point MUST match the function name in infra/kill-switch/main.py
# (currently `stop_billing`, per 00-03-SUMMARY.md). The script trusts the
# env var value; change KILL_SWITCH_FUNCTION_NAME ONLY when the symbol in
# main.py changes. --max-instances=1 caps blast radius if the function is
# invoked repeatedly.
gcloud functions deploy "$KILL_SWITCH_FUNCTION_NAME" \
  --gen2 \
  --project="$GCP_PROJECT_ID" \
  --region="$KILL_SWITCH_REGION" \
  --runtime="$KILL_SWITCH_RUNTIME" \
  --source="$REPO_ROOT/infra/kill-switch" \
  --entry-point=stop_billing \
  --trigger-topic="$KILL_SWITCH_PUBSUB_TOPIC" \
  --service-account="$SA_EMAIL" \
  --no-allow-unauthenticated \
  --max-instances=1 \
  --quiet

# ----------------------------------------------------------------------
# Section 8 — Email notification channel + budget (idempotent)
# ----------------------------------------------------------------------
EMAIL_CHANNEL=$(gcloud beta monitoring channels list \
  --project="$GCP_PROJECT_ID" \
  --filter="type=email AND labels.email_address=$ALERT_EMAIL" \
  --format='value(name)' 2>/dev/null | head -n1)

if [[ -z "$EMAIL_CHANNEL" ]]; then
  EMAIL_CHANNEL=$(gcloud beta monitoring channels create \
    --project="$GCP_PROJECT_ID" \
    --type=email \
    --display-name="Vision budget alerts" \
    --channel-labels="email_address=$ALERT_EMAIL" \
    --format='value(name)')
  echo "Created email notification channel: $EMAIL_CHANNEL"
else
  echo "Email notification channel already exists: $EMAIL_CHANNEL"
fi

EXISTING_BUDGET=$(gcloud billing budgets list \
  --billing-account="$BILLING_ACCOUNT_ID" \
  --filter="displayName=$BUDGET_DISPLAY_NAME" \
  --format="value(name)" 2>/dev/null || true)

if [[ -z "$EXISTING_BUDGET" ]]; then
  PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT_ID" \
    --format='value(projectNumber)')

  gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --display-name="$BUDGET_DISPLAY_NAME" \
    --budget-amount="${BUDGET_USD}USD" \
    --filter-projects="projects/${PROJECT_NUMBER}" \
    --threshold-rule=percent=0.5 \
    --threshold-rule=percent=0.9 \
    --threshold-rule=percent=1.0 \
    --notifications-rule-pubsub-topic="projects/$GCP_PROJECT_ID/topics/$KILL_SWITCH_PUBSUB_TOPIC" \
    --notifications-rule-monitoring-notification-channels="$EMAIL_CHANNEL"
else
  echo "Budget '$BUDGET_DISPLAY_NAME' already exists at $EXISTING_BUDGET — skipping create. To update, delete and re-run."
fi

# ----------------------------------------------------------------------
# Section 9 — Pin default compute / run regions (BOOT-04 / D-09)
# ----------------------------------------------------------------------
gcloud config set compute/region "$GCP_REGION" --project="$GCP_PROJECT_ID"
gcloud config set run/region "$GCP_REGION" --project="$GCP_PROJECT_ID"

# ----------------------------------------------------------------------
# Section 10 — Success summary
# ----------------------------------------------------------------------
echo ""
echo "============================================================"
echo "Bootstrap complete. Project=$GCP_PROJECT_ID, Region=$GCP_REGION, Budget=\$${BUDGET_USD}/mo, Kill switch=$KILL_SWITCH_FUNCTION_NAME"
echo "============================================================"
echo "  Project id:           $GCP_PROJECT_ID"
echo "  Region (single):      $GCP_REGION"
echo "  BigQuery location:    $GCP_BQ_LOCATION"
echo "  Budget:               \$${BUDGET_USD}/month (alerts at 50/90/100%)"
echo "  Alert email:          $ALERT_EMAIL"
echo "  Pub/Sub topic:        $KILL_SWITCH_PUBSUB_TOPIC"
echo "  Kill-switch function: $KILL_SWITCH_FUNCTION_NAME ($KILL_SWITCH_RUNTIME, Gen 2)"
echo "  Kill-switch SA:       $SA_EMAIL"
echo "============================================================"
echo ""
echo "Next: run ./scripts/test-kill-switch.sh against a THROWAWAY project to verify the kill switch fires before relying on it on this project. See plan 07."
