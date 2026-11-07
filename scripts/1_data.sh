#!/usr/bin/env bash
# Owner: Sanchit. Usage: bash scripts/1_data.sh
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

init_script 1_data
print_identity
require_stacks taskcloud-foundation

deploy_with_role taskcloud-data infra/1_data.yaml

section "Evidence: table status"
aws dynamodb describe-table --table-name taskcloud-tasks \
  --query 'Table.{Name:TableName,Status:TableStatus,Billing:BillingModeSummary.BillingMode}' --output table

section "Evidence: user pool"
USER_POOL_ID="$(stack_output taskcloud-data UserPoolId)"
aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" \
  --query 'UserPool.{Name:Name,AdminCreateOnly:AdminCreateUserConfig.AllowAdminCreateUserOnly}' --output table

section "Next step"
echo "Tell Aatyush to run: bash scripts/2_api.sh"
