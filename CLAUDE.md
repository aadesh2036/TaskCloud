# TaskCloud: agent instructions

## What this is
TaskCloud is a serverless student productivity app for DS3203A Cloud Computing at VIT Pune.
Students manage daily tasks, track progress and turn one typed prompt into a saved study plan using an AI agent.

## Start of every session
1. Read this file.
2. Read the "Next step" section of `docs/TILLNOW.md`.
3. Read only the docs the task needs, using the index below.

## End of every session or milestone
1. Run the tests (see the cheat sheet).
2. Update `docs/TILLNOW.md`. Never delete change-log entries. If work is half done, say exactly what remains.
3. Commit. Milestone commits use the message `M<n>: <summary>`.

## Doc index
| File | Purpose | Read when | Update when |
|---|---|---|---|
| `README.md` | Project overview, team table, local quick start | Onboarding | Setup steps or team change |
| `docs/ARCHITECTURE.md` | Source of truth for the design: services, data model, routes, agent, stacks | Changing any backend, infra or API behaviour | The design changes (with a DECISIONS entry) |
| `docs/TILLNOW.md` | Progress tracker and next step | Start of every session | After every milestone and before ending any session |
| `docs/DECISIONS.md` | Numbered decision log | Before reversing or questioning a design choice | Any sensible choice the brief did not fix, or any design change |
| `docs/DEPLOYMENT.md` | CloudShell runbook per person, troubleshooting, teardown, evidence | Deploying, or changing `scripts/` or `infra/` | Scripts, stacks or evidence change |
| `docs/IAM_ACL.md` | Access matrix, group and inline policies, service roles, console steps | Changing IAM or anything a role must do | Any permission change (with `iam/policies/` and the templates) |
| `docs/LOCAL_DEV.md` | Running and testing locally, modes, differences from AWS | Running the app locally | Local server, modes or tests change |

## Hard rules
1. Never run anything that creates, changes or deletes AWS resources. Never ask for, read or store AWS credentials. Test everything locally. The team deploys later from CloudShell.
2. Never commit secrets, account IDs, emails or generated config. Use placeholders such as `<ACCOUNT_ID>` and `<ALERT_EMAIL>`.
3. Start every AWS resource name with `taskcloud-`, and every SSM path with `/taskcloud/`, so IAM policies can be scoped by prefix.
4. `docs/ARCHITECTURE.md` is the agreed design. To change it, add an entry to `docs/DECISIONS.md` and update `docs/ARCHITECTURE.md` and `docs/IAM_ACL.md` in the same commit.
5. Keep it simple: add no services or frameworks beyond those listed. Lambda code uses only the Python standard library and the boto3 bundled with the Lambda runtime. Local Python code must run on Python 3.11 or later.
6. Track progress in `docs/TILLNOW.md`. A milestone is not done until its tests pass, TILLNOW.md is updated and the work is committed.

## Command cheat sheet
Run from the repo root. On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

| Task | Command |
|---|---|
| Install dev tools | `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` |
| Backend tests | `pytest` |
| Python lint | `ruff check backend local` |
| Template lint | `cfn-lint infra/*.yaml` |
| Script lint | `for f in scripts/*.sh scripts/lib/*.sh; do bash -n "$f"; done && shellcheck -x scripts/*.sh scripts/lib/*.sh` |
| Local API (terminal 1) | `python local/server.py` |
| Local frontend (terminal 2) | `cd frontend && npm ci && npm run dev` |
| Frontend build | `cd frontend && npm ci && npm run build` |
| Smoke test (server running) | `python local/smoke_test.py` |

## Definition of done
- All `pytest` tests pass and `ruff` is clean.
- `npm run build` succeeds.
- `cfn-lint infra/*.yaml`, `bash -n` and `shellcheck` are clean.
- `python local/smoke_test.py` passes against a running local server.
- Every file and script named in the docs exists under exactly that name.
- `docs/TILLNOW.md` is updated and the work is committed.
