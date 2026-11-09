#!/usr/bin/env bash
# Owner: Aadesh, as aadesh-admin. Usage: bash scripts/0_foundation.sh [ALERT_EMAIL] [BUDGET_LIMIT]
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

ALERT_EMAIL="${1:-${ALERT_EMAIL:-aadeshmukh236@gmail.com}}"
BUDGET_LIMIT="${2:-5}"
MODEL_ID="${MODEL_ID:-$DEFAULT_MODEL_ID}"

init_script 0_foundation
print_identity

case "$ALERT_EMAIL" in
  *@*.*) ;;
  *) fail "Usage: bash scripts/0_foundation.sh <ALERT_EMAIL> [BUDGET_LIMIT]. An email address is required for the budget alert." ;;
esac
case "$BUDGET_LIMIT" in
  '' | *[!0-9]*) fail "BUDGET_LIMIT must be a whole number of US dollars, not '$BUDGET_LIMIT'." ;;
esac

# No role here: this stack creates the deploy role that every later stack uses.
run_deploy taskcloud-foundation infra/0_foundation.yaml \
  --parameter-overrides "AlertEmail=$ALERT_EMAIL" "BudgetLimit=$BUDGET_LIMIT"

section "Model check: active inference profiles in $REGION"
aws bedrock list-inference-profiles --type-equals SYSTEM_DEFINED \
  --query "inferenceProfileSummaries[?status=='ACTIVE'].inferenceProfileId" --output table

# This does not stop the script. The stack is fine either way, and the fallback is one
# parameter. Being the first call on the account, it may also complete the Marketplace subscription.
section "Model check: one test message to $MODEL_ID"
if aws bedrock-runtime converse \
  --model-id "$MODEL_ID" \
  --messages '[{"role":"user","content":[{"text":"Reply with the word ready."}]}]' \
  --inference-config maxTokens=20 \
  --query 'output.message.content[0].text' --output text; then
  echo "Model check passed."
else
  echo "WARNING: this account could not call $MODEL_ID."
  echo "Check model access and billing in the Bedrock console, or use an Amazon Nova profile."
  echo "See 'Switching to Amazon Nova' in docs/DEPLOYMENT.md."
fi

section "Next steps"
echo "1. Run: bash scripts/render_iam.sh, then create the users and group from docs/IAM_ACL.md."
echo "2. Tell Sanchit to run: bash scripts/1_data.sh"
