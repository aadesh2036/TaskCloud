# TILLNOW

## Last updated
2026-11-07 10:36 IST, by Claude Code session (M1)

## Current state
The backend task API and attachment indexer work and are tested against DynamoDB and S3 (moto) and the local JSON store. There is no planner, server or UI yet.

## Milestones
| ID | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Repo and tracking docs | Done | |
| M1 | Backend: shared code, tasks-api, attachment-indexer, tests | Done | 135 tests, both store backends |
| M2 | Planner agent with fake Bedrock client | Not started | |
| M3 | Local dev server | Not started | |
| M4 | React + Vite frontend | Not started | |
| M5 | CloudFormation templates | Not started | |
| M6 | Deploy scripts | Not started | |
| M7 | IAM policy files and IAM_ACL.md | Not started | |
| M8 | Full local verification and smoke test | Not started | |
| M9 | Final docs pass | Not started | |

## Next step
Start M2: write `backend/functions/planner_agent/handler.py` and its tests with a fake Bedrock client.

## Open questions and blockers
- None yet.

## Change log
### 2026-11-07 10:36 IST, M1
- **Files:** `backend/shared/*`, `backend/functions/tasks_api/handler.py`, `backend/functions/attachment_indexer/handler.py`, `backend/tests/*`, `pyproject.toml`
- **Tests:** pytest 135 passed; ruff clean
- **Decisions:** D-014 to D-017 implemented

### 2026-11-07 10:40 IST, M0
- **Files:** `CLAUDE.md`, `AGENTS.md`, `README.md`, `requirements-dev.txt`, `.gitignore`, `.gitattributes`, `docs/*`, folder layout. Moved `TaskCloud_Cloud_Architecture.pdf` to `docs/`.
- **Tests:** none yet (no code).
- **Decisions:** D-001 to D-018 recorded.
