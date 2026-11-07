# TILLNOW

## Last updated
2026-11-07 10:40 IST, by Claude Code session (M0)

## Current state
The repository is initialized with its layout and tracking docs. No application code exists yet, so nothing runs.

## Milestones
| ID | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Repo and tracking docs | Done | |
| M1 | Backend: shared code, tasks-api, attachment-indexer, tests | Not started | |
| M2 | Planner agent with fake Bedrock client | Not started | |
| M3 | Local dev server | Not started | |
| M4 | React + Vite frontend | Not started | |
| M5 | CloudFormation templates | Not started | |
| M6 | Deploy scripts | Not started | |
| M7 | IAM policy files and IAM_ACL.md | Not started | |
| M8 | Full local verification and smoke test | Not started | |
| M9 | Final docs pass | Not started | |

## Next step
Start M1: write `backend/shared/` (validation, responses, store) and `backend/functions/tasks_api/handler.py`.

## Open questions and blockers
- None yet.

## Change log
### 2026-11-07 10:40 IST, M0
- **Files:** `CLAUDE.md`, `AGENTS.md`, `README.md`, `requirements-dev.txt`, `.gitignore`, `.gitattributes`, `docs/*`, folder layout. Moved `TaskCloud_Cloud_Architecture.pdf` to `docs/`.
- **Tests:** none yet (no code).
- **Decisions:** D-001 to D-018 recorded.
