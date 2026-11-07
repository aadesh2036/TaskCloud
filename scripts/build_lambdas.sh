#!/usr/bin/env bash
# Fills .build/<function> with that function's code plus backend/shared.
# The templates point at these folders, and `aws cloudformation package` zips them.
# Lambda provides boto3, so nothing is installed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

rm -rf .build
for fn in tasks_api attachment_indexer planner_agent; do
  mkdir -p ".build/$fn"
  cp "backend/functions/$fn/"*.py ".build/$fn/"
  cp -R backend/shared ".build/$fn/shared"
  # Compiled files would change the zip hash and make every deploy look like a code change.
  find ".build/$fn" -type d -name __pycache__ -prune -exec rm -rf {} +
  echo "Built .build/$fn"
done
