#!/usr/bin/env bash
# Shared by every TaskCloud script. Source it, then call init_script.

REGION="${TASKCLOUD_REGION:-ap-south-1}"
export AWS_REGION="$REGION" AWS_DEFAULT_REGION="$REGION"
# Without this, the CLI can stop and wait in a pager, which hangs a script.
export AWS_PAGER=""

# shellcheck disable=SC2034  # Used by the scripts that source this file.
DEFAULT_MODEL_ID="apac.amazon.nova-lite-v1:0"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -f "$REPO_ROOT/.env" ]; then
  # shellcheck source=/dev/null
  set -a
  source "$REPO_ROOT/.env"
  set +a
fi
LOG_FILE=""
TEE_PID=""

# shellcheck disable=SC2329  # Called through the EXIT trap below.
on_exit() {
  local status=$?
  trap - EXIT
  if [ "$status" -ne 0 ]; then
    echo
    echo "FAILED (exit code $status)."
    echo "Do not fix this in the console. Send this log file to Aadesh."
    echo "Log file: $LOG_FILE"
  else
    echo
    echo "Log file: $LOG_FILE"
  fi
  # Let tee finish writing, so the last lines reach the log before the prompt returns.
  exec 1>&- 2>&-
  [ -n "$TEE_PID" ] && wait "$TEE_PID" 2>/dev/null
  exit "$status"
}

# Sends all output to the screen and logs/<script>_<YYYYMMDD-HHMMSS>.log, and installs the failure message.
init_script() {
  local name="$1"
  mkdir -p "$REPO_ROOT/logs"
  LOG_FILE="$REPO_ROOT/logs/${name}_$(date +%Y%m%d-%H%M%S).log"
  exec > >(tee -a "$LOG_FILE") 2>&1
  TEE_PID=$!
  trap on_exit EXIT
  cd "$REPO_ROOT" || exit 1
  echo "=== $name, started $(date) ==="
}

fail() {
  echo "ERROR: $*"
  exit 1
}

section() {
  echo
  echo "--- $* ---"
}

print_identity() {
  section "Who is running this"
  aws sts get-caller-identity --output table
  echo "Region: $REGION"
}

stack_status() {
  aws cloudformation describe-stacks --stack-name "$1" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "MISSING"
}

# Stops with a clear message unless every named stack has finished deploying.
require_stacks() {
  section "Checking prerequisite stacks"
  local stack status
  for stack in "$@"; do
    status="$(stack_status "$stack")"
    case "$status" in
      CREATE_COMPLETE | UPDATE_COMPLETE)
        echo "$stack: $status"
        ;;
      *)
        fail "Prerequisite stack $stack is not ready (status: $status). Its owner must finish deploying it first. See docs/DEPLOYMENT.md for the order."
        ;;
    esac
  done
}

stack_output() {
  aws cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text
}

get_export() {
  aws cloudformation list-exports \
    --query "Exports[?Name=='$1'].Value | [0]" --output text
}

print_stack_report() {
  local stack="$1"
  section "Stack status: $stack"
  aws cloudformation describe-stacks --stack-name "$stack" \
    --query 'Stacks[0].StackStatus' --output text
  section "Last 20 events: $stack"
  aws cloudformation describe-stack-events --stack-name "$stack" --max-items 20 \
    --query 'StackEvents[].[Timestamp,LogicalResourceId,ResourceStatus,ResourceStatusReason]' \
    --output table
  section "Outputs: $stack"
  aws cloudformation describe-stacks --stack-name "$stack" \
    --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output table
}

# A stack whose first create failed cannot be updated, only deleted. Team users cannot
# delete stacks, on purpose, so this gives a clear message rather than a confusing CLI error.
stop_if_rolled_back() {
  local stack="$1"
  local status
  status="$(stack_status "$stack")"
  if [ "$status" = "ROLLBACK_COMPLETE" ]; then
    fail "Stack $stack is in ROLLBACK_COMPLETE state because its first create failed. Aadesh must read its events, delete it, fix the cause, and then this script can be re-run."
  fi
}

# Deploys a template, printing the report whether it worked or not. Extra arguments go to deploy.
run_deploy() {
  local stack="$1" template="$2"
  shift 2
  stop_if_rolled_back "$stack"
  section "Deploying $stack"
  if ! aws cloudformation deploy \
    --stack-name "$stack" \
    --template-file "$template" \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    "$@"; then
    print_stack_report "$stack" || true
    fail "Deploying $stack failed. The events above usually name the cause."
  fi
  print_stack_report "$stack"
}

# All stacks except the foundation deploy through the shared deploy role.
deploy_with_role() {
  local stack="$1" template="$2"
  shift 2
  local role_arn
  role_arn="$(get_export taskcloud-foundation-CfnRoleArn)"
  if [ -z "$role_arn" ] || [ "$role_arn" = "None" ]; then
    fail "Export taskcloud-foundation-CfnRoleArn was not found. Aadesh must run scripts/0_foundation.sh first."
  fi
  run_deploy "$stack" "$template" --role-arn "$role_arn" "$@"
}

# Uploads Lambda code to the artifact bucket and writes packaged-<name>.yaml, which is
# the same template with each local Code path replaced by its S3 location.
package_template() {
  local name="$1"
  local bucket
  bucket="$(get_export taskcloud-foundation-ArtifactBucket)"
  section "Packaging $name into $bucket"
  aws cloudformation package \
    --template-file "infra/$name.yaml" \
    --s3-bucket "$bucket" \
    --s3-prefix lambda \
    --output-template-file "packaged-$name.yaml"
}
