#!/usr/bin/env bash
# Owner: Aadesh. Usage: bash scripts/create_demo_user.sh <DEMO_EMAIL>
# The password is prompted for, so it never reaches the log file or the shell history.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

DEMO_EMAIL="${1:-}"

init_script create_demo_user
print_identity

case "$DEMO_EMAIL" in
  *@*.*) ;;
  *) fail "Usage: bash scripts/create_demo_user.sh <DEMO_EMAIL>" ;;
esac

require_stacks taskcloud-data
USER_POOL_ID="$(stack_output taskcloud-data UserPoolId)"

echo "Choose a password with at least 8 characters, including upper case, lower case and a number."
read -r -s -p "Password: " DEMO_PASSWORD
echo
[ -n "$DEMO_PASSWORD" ] || fail "The password cannot be empty."

# Safe to re-run: an existing user just gets the new password.
if aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$DEMO_EMAIL" >/dev/null 2>&1; then
  echo "User already exists, so only the password will change."
else
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$DEMO_EMAIL" \
    --user-attributes "Name=email,Value=$DEMO_EMAIL" Name=email_verified,Value=true \
    --message-action SUPPRESS \
    --query 'User.UserStatus' --output text
fi

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$DEMO_EMAIL" \
  --password "$DEMO_PASSWORD" \
  --permanent

echo "Demo user is ready: $DEMO_EMAIL"
