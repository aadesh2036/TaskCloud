#!/usr/bin/env bash
# Owner: Aadesh. Usage: bash scripts/3_agent.sh
# Re-run this after any update to the API stack, which can reset the /plan throttle (D-009).
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

init_script 3_agent
print_identity
require_stacks taskcloud-foundation taskcloud-data taskcloud-api

# A re-run keeps the current model, so it cannot silently undo a switch to Nova.
CURRENT_MODEL="$(aws ssm get-parameter --name /taskcloud/modelId \
  --query 'Parameter.Value' --output text 2>/dev/null || true)"
MODEL_ID="${MODEL_ID:-${CURRENT_MODEL:-$DEFAULT_MODEL_ID}}"
echo "Model: $MODEL_ID"

section "Building Lambda code"
bash scripts/build_lambdas.sh

package_template 3_agent
deploy_with_role taskcloud-agent packaged-3_agent.yaml --parameter-overrides "ModelId=$MODEL_ID"

# CloudFormation rejects stage RouteSettings for a route key made in another stack,
# so the throttle is applied directly.
section "Applying the /plan throttle (burst 2, rate 2)"
API_ID="$(stack_output taskcloud-api ApiId)"
API_ENDPOINT="$(stack_output taskcloud-api ApiEndpoint)"
# shellcheck disable=SC2016  # $default is the stage's literal name, not a variable.
aws apigatewayv2 update-stage \
  --api-id "$API_ID" \
  --stage-name '$default' \
  --route-settings '{"POST /plan":{"ThrottlingBurstLimit":2,"ThrottlingRateLimit":2}}' \
  --query 'RouteSettings' --output json

section "End-to-end test"
cat <<TESTCMD
Create a demo user if you have not: bash scripts/create_demo_user.sh <DEMO_EMAIL>
Log in to the site, open the browser's developer tools, and copy the value of the
localStorage key ending in .idToken. Then run:

  export TOKEN='<PASTE_ID_TOKEN>'
  curl -i -X POST "$API_ENDPOINT/plan" \\
    -H "Authorization: Bearer \$TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"prompt":"DBMS exam on Friday, finish my lab record, and revise two hours a day."}'

Expect HTTP 200 with a summary and saved tasks. The same request with no token must return 401.
TESTCMD

section "Next step"
echo "Tell Krushna to run: bash scripts/4_frontend.sh"
