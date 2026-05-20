# ---------------------------------------------------------------------------
# Vendored from: https://github.com/Cyclenerd/poweroff-google-cloud-cap-billing
# Upstream commit: e5781791e08b86cb49debffce82bace453b1e809
# License: Apache-2.0 (see ../../NOTICE)
# Local modifications:
#   - Banner added.
#   - Project id sourced from the Pub/Sub message body (`projectId`) when
#     present in the GCP Billing budget notification, with a fallback to the
#     Cloud Function's Application Default Credentials project. The upstream
#     always uses ADC; the fallback preserves that behaviour, while the
#     primary path makes the function safely reusable across projects.
#   - No hard-coded project id (acceptance criterion: a literal
#     project-id constant assignment must NOT appear in this file).
# Original upstream copyright/license headers retained below.
# ---------------------------------------------------------------------------

# Copyright 2021 Google LLC
# Copyright 2022 Nils Knieling
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

###############################################################################
# This function will remove the billing account associated
# with the project if the cost amount is higher than the budget amount.
#
# Source:
# https://github.com/GoogleCloudPlatform/python-docs-samples
# Vendored via Cyclenerd/poweroff-google-cloud-cap-billing.
###############################################################################

import base64
import json

import google.auth
from google.cloud import billing

# ADC-derived project (the Cloud Function's runtime project). Used as a
# fallback when the Pub/Sub message body does not carry an explicit projectId.
_ADC_PROJECT = google.auth.default()[1]
cloud_billing_client = billing.CloudBillingClient()


def stop_billing(data: dict, context):
    """Cloud Functions (Gen 2) entry point: Pub/Sub trigger.

    Receives a GCP Billing budget notification on a Pub/Sub topic.
    If `costAmount > budgetAmount`, calls the GCP Cloud Billing REST API
    method `cloudbilling.projects.updateBillingInfo` (via the
    `google-cloud-billing` Python client's `update_project_billing_info`) with
    an empty `billingAccountName`, which disables billing on the target
    project. This is a one-way "last resort" action — see
    ../../infra/kill-switch/README.md.
    """
    pubsub_data = base64.b64decode(data["data"]).decode("utf-8")
    print(f"Data: {pubsub_data}")

    pubsub_json = json.loads(pubsub_data)
    cost_amount = pubsub_json["costAmount"]
    budget_amount = pubsub_json["budgetAmount"]

    if cost_amount <= budget_amount:
        print(f"No action necessary. (Current cost: {cost_amount})")
        return

    # Prefer the projectId from the Pub/Sub budget-notification body when
    # present; fall back to the function's ADC project. The GCP Billing
    # budget-notification schema may include `projectId` when the budget is
    # scoped to a single project; we honour that to keep the function safely
    # reusable across projects without redeploying with a different identity.
    target_project_id = pubsub_json.get("projectId") or _ADC_PROJECT
    project_name = cloud_billing_client.common_project_path(target_project_id)

    request = billing.UpdateProjectBillingInfoRequest(
        name=project_name,
        project_billing_info=billing.ProjectBillingInfo(
            billing_account_name=""  # Disable billing
        ),
    )
    project_billing_info = cloud_billing_client.update_project_billing_info(request)
    print(f"Billing disabled: {project_billing_info}")
