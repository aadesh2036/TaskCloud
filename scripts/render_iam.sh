#!/usr/bin/env bash
# Owner: Aadesh. Usage: bash scripts/render_iam.sh [ACCOUNT_ID]
# Fills the account ID into iam/policies/*.json and writes iam/rendered/, which git ignores.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

ACCOUNT_ID="${1:-}"

init_script render_iam

if [ -z "$ACCOUNT_ID" ]; then
  print_identity
  ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
fi
case "$ACCOUNT_ID" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) fail "An account ID must be 12 digits, not '$ACCOUNT_ID'." ;;
esac

mkdir -p iam/rendered
for policy in iam/policies/*.json; do
  target="iam/rendered/$(basename "$policy")"
  sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" "$policy" > "$target"
  python3 -m json.tool "$target" > /dev/null || fail "$target is not valid JSON."
  echo "Wrote $target"
done

echo "Paste these into the console, following docs/IAM_ACL.md."
