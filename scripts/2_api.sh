#!/usr/bin/env bash
# Owner: Aatyush. Usage: bash scripts/2_api.sh
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

init_script 2_api
print_identity
require_stacks taskcloud-foundation taskcloud-data

section "Building Lambda code"
bash scripts/build_lambdas.sh

package_template 2_api
deploy_with_role taskcloud-api packaged-2_api.yaml

section "Evidence: GET /tasks with no token must return 401"
API_ENDPOINT="$(stack_output taskcloud-api ApiEndpoint)"
BODY_FILE="$(mktemp)"
HTTP_CODE=""
# The $default stage auto-deploys, so a brand new API can take a few seconds to respond.
for _ in 1 2 3 4 5 6; do
  HTTP_CODE="$(curl --silent --output "$BODY_FILE" --write-out '%{http_code}' "$API_ENDPOINT/tasks" || true)"
  [ "$HTTP_CODE" = "401" ] && break
  sleep 5
done
echo "GET $API_ENDPOINT/tasks returned HTTP $HTTP_CODE"
cat "$BODY_FILE"
echo
rm -f "$BODY_FILE"
if [ "$HTTP_CODE" != "401" ]; then
  fail "Expected 401 from a request with no token, but got $HTTP_CODE."
fi

section "Next step"
echo "Tell Aadesh to run: bash scripts/3_agent.sh"
echo "If this was an update to an existing API, Aadesh must re-run it too, to restore the /plan throttle."
