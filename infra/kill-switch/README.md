# Billing Kill Switch (vendored)

Pub/Sub → Cloud Function (Gen 2) that disables billing on the GCP project when a
budget-notification reports `costAmount > budgetAmount`. Vendored from
Cyclenerd/poweroff-google-cloud-cap-billing per D-04 of
`.planning/phases/00-bootstrap-cost-guardrails/00-CONTEXT.md`.

## Upstream

- Repo: https://github.com/Cyclenerd/poweroff-google-cloud-cap-billing
- Vendored at upstream commit: `e5781791e08b86cb49debffce82bace453b1e809`
- License: Apache-2.0
- Vendored on: 2026-05-20
- See ../../NOTICE for full attribution.

## Entry point and runtime

- Source file: `main.py`
- Entry-point function: `stop_billing` (Pub/Sub-triggered, Cloud Functions Gen 2)
- Python runtime: `python312`
- Pub/Sub message contract: GCP Billing budget-notification JSON. The function
  expects `costAmount` and `budgetAmount` fields in the decoded message body;
  it also honours an optional `projectId` field for cross-project reusability.

## What it does

- Listens on a Pub/Sub topic for GCP Billing budget notifications.
- On `costAmount > budgetAmount`, calls the Cloud Billing API method
  `cloudbilling.projects.updateBillingInfo(name=<project>, body={"billingAccountName": ""})`,
  which disables billing on the project.
- Logs the action via Cloud Function logs (visible in Cloud Logging).

## ⚠ This is a one-way door

Disabling billing also stops all running services after a short delay. To
recover, the operator must manually re-link the project to a billing account
via `gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ACCOUNT_ID>`
or via the Cloud Console UI. **This kill switch is a LAST RESORT**; the budget
alerts at 50/90/100% (configured in plan 04) should normally surface the
problem before the 100% threshold trips this function.

## Deployment

Deployed by `scripts/bootstrap-gcp.sh` (plan 04). Do not deploy manually — the
script wires the Pub/Sub topic, the budget alert, and the function together
correctly (region, service-account identity, IAM role grants).

## Testing

Tested end-to-end by `scripts/test-kill-switch.sh` (plan 04, operator-run in
plan 07). The test publishes a synthetic budget-exceeded message to the
Pub/Sub topic and verifies:

1. The function logs the disable-billing action.
2. `gcloud billing projects describe $PROJECT_ID --format='value(billingEnabled)'`
   returns `False`.

The test MUST be run against a throwaway project per D-06 — it really does
disable billing on whatever project the function is deployed to.

## Local modifications vs upstream

- Banner comment block referencing the upstream URL, commit SHA, and license.
- `target_project_id` is sourced from the Pub/Sub message body's `projectId`
  field when present, with a fallback to the function's Application Default
  Credentials project. Upstream uses ADC unconditionally; the fallback
  preserves that behaviour while letting a single deployed function safely
  disable billing on the project the budget notification names.
- No hard-coded `PROJECT_ID = "..."` constant anywhere in `main.py`.
- Upstream `google-cloud-billing==1.19.0` pin kept; `google-auth` added as an
  explicit pin to stabilize the dependency graph across minor releases.

## References

- GCP Billing budget notifications: https://cloud.google.com/billing/docs/how-to/notify
- Disable billing on a project: https://cloud.google.com/billing/docs/how-to/disable-billing-with-notifications
- Cloud Functions Gen 2 deployment: https://cloud.google.com/functions/docs/concepts/version-comparison
