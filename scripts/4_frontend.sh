#!/usr/bin/env bash
# Owner: Krushna. Usage: bash scripts/4_frontend.sh
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

BRANCH="main"
MAX_POLLS=60
POLL_SECONDS=5

init_script 4_frontend
print_identity

section "Checking Node"
command -v node >/dev/null || fail "Node is not installed. CloudShell normally includes it."
echo "node $(node -v)"
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 18 ]; then
  fail "Node 18 or later is required, but this is $(node -v)."
fi

require_stacks taskcloud-foundation taskcloud-data taskcloud-api taskcloud-agent

deploy_with_role taskcloud-frontend infra/4_frontend.yaml

section "Reading stack outputs"
USER_POOL_ID="$(stack_output taskcloud-data UserPoolId)"
USER_POOL_CLIENT_ID="$(stack_output taskcloud-data UserPoolClientId)"
API_ENDPOINT="$(stack_output taskcloud-api ApiEndpoint)"
APP_ID="$(stack_output taskcloud-frontend AmplifyAppId)"
SITE_URL="$(stack_output taskcloud-frontend SiteUrl)"
echo "API: $API_ENDPOINT"
echo "Amplify app: $APP_ID"

section "Building the site"
(cd frontend && npm ci && npm run build)

# Written after the build, so these values never go through the bundler or into git.
REGION="$REGION" API_ENDPOINT="$API_ENDPOINT" USER_POOL_ID="$USER_POOL_ID" \
  USER_POOL_CLIENT_ID="$USER_POOL_CLIENT_ID" python3 - <<'PY'
import json, os
config = {
    "mode": "aws",
    "region": os.environ["REGION"],
    "apiUrl": os.environ["API_ENDPOINT"],
    "userPoolId": os.environ["USER_POOL_ID"],
    "userPoolClientId": os.environ["USER_POOL_CLIENT_ID"],
}
with open("frontend/dist/config.json", "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2)
PY
echo "Wrote frontend/dist/config.json"

section "Zipping the contents of dist/"
ZIP_FILE="$REPO_ROOT/.build/frontend.zip"
mkdir -p "$REPO_ROOT/.build"
rm -f "$ZIP_FILE"
# From inside dist/, because Amplify needs index.html at the top level of the zip.
(cd frontend/dist && zip -qr "$ZIP_FILE" .)
ls -lh "$ZIP_FILE"

section "Uploading to Amplify"
# D-008: the upload URL route avoids turning on S3 ACLs. It is a secret, so it is not printed.
read -r JOB_ID UPLOAD_URL < <(aws amplify create-deployment \
  --app-id "$APP_ID" --branch-name "$BRANCH" \
  --query '[jobId,zipUploadUrl]' --output text)
[ -n "${UPLOAD_URL:-}" ] || fail "Amplify did not return an upload URL."
curl --fail --silent --show-error -X PUT \
  -H 'Content-Type: application/zip' \
  --upload-file "$ZIP_FILE" "$UPLOAD_URL"
echo "Uploaded. Job: $JOB_ID"

section "Starting the deployment"
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" \
  --query 'jobSummary.status' --output text

STATUS="UNKNOWN"
for ((i = 1; i <= MAX_POLLS; i++)); do
  STATUS="$(aws amplify get-job --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" \
    --query 'job.summary.status' --output text)"
  echo "Job $JOB_ID: $STATUS"
  case "$STATUS" in
    SUCCEED) break ;;
    FAILED | CANCELLED) fail "The Amplify deployment ended with status $STATUS." ;;
  esac
  sleep "$POLL_SECONDS"
done
[ "$STATUS" = "SUCCEED" ] || fail "The deployment did not finish in time. Last status: $STATUS."

section "Done"
echo "Site URL: $SITE_URL"
echo "Open it and check that the login page appears."
