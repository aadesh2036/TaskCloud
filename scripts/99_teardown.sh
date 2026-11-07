#!/usr/bin/env bash
# Owner: Aadesh, as aadesh-admin. Usage: bash scripts/99_teardown.sh
# Deletes everything TaskCloud created. Safe to re-run if interrupted.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

init_script 99_teardown
print_identity

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ATTACHMENTS_BUCKET="taskcloud-attachments-$ACCOUNT_ID-$REGION"
ARTIFACT_BUCKET="taskcloud-artifacts-$ACCOUNT_ID-$REGION"
TRAIL_BUCKET="taskcloud-trail-$ACCOUNT_ID-$REGION"

section "This permanently deletes all TaskCloud stacks and data"
echo "Tasks, user accounts, attachments, Lambda code and audit logs will all be removed."
read -r -p "Type DELETE to continue: " CONFIRM
if [ "$CONFIRM" != "DELETE" ]; then
  echo "Nothing was deleted."
  exit 0
fi

empty_bucket() {
  local bucket="$1"
  if aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
    echo "Emptying $bucket"
    aws s3 rm "s3://$bucket" --recursive --only-show-errors
  fi
}

empty_buckets() {
  local bucket
  for bucket in "$@"; do
    empty_bucket "$bucket"
  done
}

# Usage: delete_stack <stack> [bucket ...]. CloudFormation cannot delete a non-empty bucket.
delete_stack() {
  local stack="$1"
  shift
  section "Deleting $stack"
  if [ "$(stack_status "$stack")" = "MISSING" ]; then
    echo "$stack does not exist, so there is nothing to do."
    return 0
  fi
  empty_buckets "$@"
  aws cloudformation delete-stack --stack-name "$stack"
  if aws cloudformation wait stack-delete-complete --stack-name "$stack"; then
    echo "Deleted $stack"
    return 0
  fi
  # CloudTrail can deliver one last file after the bucket was emptied, so try once more.
  echo "First delete attempt failed. Emptying buckets and retrying."
  empty_buckets "$@"
  aws cloudformation delete-stack --stack-name "$stack"
  if ! aws cloudformation wait stack-delete-complete --stack-name "$stack"; then
    print_stack_report "$stack" || true
    fail "Could not delete $stack. Its events are above. Fix the cause and re-run this script."
  fi
  echo "Deleted $stack"
}

delete_stack taskcloud-frontend
delete_stack taskcloud-agent
delete_stack taskcloud-api "$ATTACHMENTS_BUCKET"
delete_stack taskcloud-data

# Stop new audit logs first, or the trail bucket would keep refilling while it is deleted.
section "Stopping the audit trail"
aws cloudtrail stop-logging --name taskcloud-trail 2>/dev/null || echo "Trail is not running."
delete_stack taskcloud-foundation "$ARTIFACT_BUCKET" "$TRAIL_BUCKET"

section "Teardown finished"
echo "Now delete the IAM users, group and policy by hand. See docs/IAM_ACL.md."
echo "Check AWS Budgets and Billing again tomorrow."
