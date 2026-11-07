# TILLNOW

## Last updated
2026-11-07 10:58 IST, by Claude Code session (M6)

## Current state
The local app, templates and deploy scripts are complete. Script flow, order and failure handling are tested against a fake aws CLI, and nothing has been run against real AWS.

## Milestones
| ID | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Repo and tracking docs | Done | |
| M1 | Backend: shared code, tasks-api, attachment-indexer, tests | Done | 135 tests, both store backends |
| M2 | Planner agent with fake Bedrock client | Done | Fake Bedrock client; injection tests included |
| M3 | Local dev server | Done | Standard library only; verified on bare Python 3.11 |
| M4 | React + Vite frontend | Done | Builds on Node 18 and 20; browser-tested |
| M5 | CloudFormation templates | Done | cfn-lint clean; design checks in test_infra.py |
| M6 | Deploy scripts | Done | bash -n and shellcheck clean; flow tested with a fake aws CLI |
| M7 | IAM policy files and IAM_ACL.md | Not started | |
| M8 | Full local verification and smoke test | Not started | |
| M9 | Final docs pass | Not started | |

## Next step
Start M7: write `iam/policies/*.json` and test them against what the scripts call.

## Open questions and blockers
- None yet.

## Change log
### 2026-11-07 10:58 IST, M6
- **Files:** `scripts/*`, `backend/tests/test_scripts.py`, `docs/DEPLOYMENT.md`
- **Tests:** pytest 352 passed; shellcheck clean; bash -n clean
- **Decisions:** None

### 2026-11-07 10:55 IST, M5
- **Files:** `infra/*.yaml`, `backend/tests/test_infra.py`, `docs/DECISIONS.md`
- **Tests:** cfn-lint clean; pytest all passed
- **Decisions:** D-019, D-020, D-021, D-022

### 2026-11-07 10:49 IST, M4
- **Files:** `frontend/*`
- **Tests:** npm ci and build on Node 18.20 and 20.20 and 24; headless Chromium flow for add, complete, plan, attach, open, oversize, edit, delete, mobile (no overflow, no console errors); real aws-amplify against a mocked Cognito for login, wrong password, new password, reload, 401 sign-out
- **Decisions:** None

### 2026-11-07 10:41 IST, M3
- **Files:** `local/server.py`, `local/stub_bedrock.py`, `local/smoke_test.py`, `backend/tests/test_local_server.py`
- **Tests:** pytest 240 passed on Python 3.11, 3.13 and 3.14; smoke test passed on bare 3.11 without boto3; ruff clean
- **Decisions:** None

### 2026-11-07 10:38 IST, M2
- **Files:** `backend/functions/planner_agent/handler.py`, `backend/tests/test_planner.py`
- **Tests:** pytest 235 passed; ruff clean
- **Decisions:** D-018 implemented

### 2026-11-07 10:36 IST, M1
- **Files:** `backend/shared/*`, `backend/functions/tasks_api/handler.py`, `backend/functions/attachment_indexer/handler.py`, `backend/tests/*`, `pyproject.toml`
- **Tests:** pytest 135 passed; ruff clean
- **Decisions:** D-014 to D-017 implemented

### 2026-11-07 10:32 IST, M0
- **Files:** `CLAUDE.md`, `AGENTS.md`, `README.md`, `requirements-dev.txt`, `.gitignore`, `.gitattributes`, `docs/*`, folder layout. Moved `TaskCloud_Cloud_Architecture.pdf` to `docs/`.
- **Tests:** none yet (no code).
- **Decisions:** D-001 to D-018 recorded.
