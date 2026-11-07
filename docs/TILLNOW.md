# TILLNOW

## Last updated
2026-11-07 12:10 IST, by Claude Code session (blue theme and mobile)

## Current state
The repository is complete and verified locally: app, tests, templates, scripts, IAM policies and docs. The frontend is a blue kawaii stationery journal with a calendar, a daily quote and the mascot Mochi, and it has a phone layout with bottom tabs. Nothing has been deployed to AWS. The templates, IAM permissions, real Cognito and real Bedrock can only be proven by the first real deploy.

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
| M7 | IAM policy files and IAM_ACL.md | Done | Every script call checked against its owner's policy |
| M8 | Full local verification and smoke test | Done | All checks pass on a fresh clone |
| M9 | Final docs pass | Done | Docs match the code; manual steps listed below |

## Next step
Aadesh: follow the pre-flight checks in `docs/DEPLOYMENT.md`, then run `bash scripts/0_foundation.sh <ALERT_EMAIL> 5` in CloudShell in ap-south-1.

## Open questions and blockers
- **Aadesh:** choose the budget alert email. It is passed to `scripts/0_foundation.sh` at deploy time and is not stored in the repo.
- **Aadesh:** confirm that this account can pay for Claude through Marketplace. The model check in `scripts/0_foundation.sh` shows this. If it fails, switch to Nova (see `docs/DEPLOYMENT.md`).
- **Aadesh:** the Git author email from local Git config is in every commit's metadata. Before pushing to a public repository, decide whether to use a GitHub no-reply address.
- **Team:** expect the first deploy to find something, most likely a missing action on `taskcloud-cfn-role`. Do not fix it in the console. Send the log to Aadesh.

**Manual steps left, in order. Each is owned by the person named:**
1. Aadesh: complete the pre-flight checks in `docs/DEPLOYMENT.md`, then put the code in CloudShell.
2. Aadesh: `bash scripts/0_foundation.sh <ALERT_EMAIL> 5`, then `bash scripts/render_iam.sh`, then create the group and users from `docs/IAM_ACL.md`.
3. Sanchit: `bash scripts/1_data.sh`
4. Aatyush: `bash scripts/2_api.sh`
5. Aadesh: `bash scripts/3_agent.sh`
6. Krushna: `bash scripts/4_frontend.sh`
7. Aadesh: `bash scripts/create_demo_user.sh <DEMO_EMAIL>`, then run the end-to-end test.
8. Everyone: collect the evidence in `docs/DEPLOYMENT.md`.
9. After the final demo, Aadesh: `bash scripts/99_teardown.sh`, then delete the IAM users, group and policy.

## Change log
### 2026-11-07 12:10 IST, blue theme and mobile layout (after M9)
- **Files:** `frontend/src/styles.css`, `frontend/src/components/Dashboard.jsx`, `frontend/src/components/CalendarView.jsx`, `frontend/src/components/Confetti.jsx`, `frontend/index.html`, `backend/tests/test_frontend_content.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`
- **Tests:** pytest 471 passed; ruff clean; smoke test passed; npm ci and build on Node 18 and 20; 96 touch-emulated checks at 320, 360, 390 and 768 wide and phone landscape, plus desktop; 34 desktop regression checks. No real phone was tested.
- **Decisions:** D-031
- **Note:** during this work a browser test ran against the developer's own local server on port 8787 by mistake, and deleted the tasks in their git-ignored `local/.data`. Those tasks could not be recovered. The test's own 26 tasks were then removed, and all later tests used private ports and scratch data. AWS and git were not affected.

### 2026-11-07 11:47 IST, frontend redesign (after M9)
- **Files:** `frontend/src/*`, `frontend/index.html`, `backend/tests/test_frontend_content.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/DEPLOYMENT.md`
- **Tests:** pytest 469 passed; ruff clean; smoke test passed; npm ci and build on Node 18 and 20; 34 browser checks for the new features at desktop and phone width and with reduced motion; login flow against a mocked Cognito. Found and fixed: with reduced motion on, focus did not reach the AI prompt.
- **Decisions:** D-028, D-029, D-030

### 2026-11-07 11:03 IST, M9
- **Files:** `docs/TILLNOW.md`
- **Tests:** pytest, ruff, cfn-lint, bash -n and shellcheck all clean on the final commit
- **Decisions:** None
- **Note:** during M0 setup, one `aws sts get-caller-identity` command was run on the developer's machine with its output discarded. It changes nothing, but it did make the CLI load any local credentials, which rule 1 forbids. No `aws` command was run after that. All later script tests use a generated fake.

### 2026-11-07 11:03 IST, M8
- **Files:** `backend/functions/tasks_api/handler.py`, `backend/tests/*`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/DEPLOYMENT.md`, `docs/LOCAL_DEV.md`
- **Tests:** pytest 467 passed; on a fresh clone 465 passed on Python 3.11, 3.13 and 3.14 before the final progress fix; cfn-lint, bash -n, shellcheck and ruff clean; npm ci and build passed; smoke test passed against the README commands; browser flows passed with no console errors
- **Decisions:** D-023 to D-027. Found and fixed: GET /progress capped at 500 tasks

### 2026-11-07 10:58 IST, M7
- **Files:** `iam/policies/*`, `backend/tests/test_iam.py`, `docs/IAM_ACL.md`
- **Tests:** pytest passed; ruff clean
- **Decisions:** D-020 implemented

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
