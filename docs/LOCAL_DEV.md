# Local development

The whole app runs on one machine with no AWS account. Use Python 3.11 or later and Node 18 or later.

## Run the app

The local server uses only the standard library, so it needs no `pip install`.

| Terminal | Windows PowerShell | Linux or macOS |
|---|---|---|
| 1. API | `python local\server.py` | `python3 local/server.py` |
| 2. Frontend | `cd frontend; npm ci; npm run dev` | `cd frontend && npm ci && npm run dev` |

Open http://localhost:5173. `npm run dev` creates `frontend/public/config.json` from `frontend/config.local.example.json` if it does not exist.

## Run the tests

Install the dev tools once, in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

| Check | Command |
|---|---|
| Backend, script, template and IAM tests | `pytest` |
| Python lint | `ruff check backend local` |
| Templates | `cfn-lint infra/*.yaml` |
| Scripts | `bash -n scripts/1_data.sh` (and the others), `shellcheck -x scripts/*.sh scripts/lib/*.sh` |
| Frontend build | `cd frontend && npm run build` |
| End-to-end smoke test, with the local server running | `python local/smoke_test.py` |

`pytest` covers more than the Python code, and none of it can reach AWS:

| File | What it checks |
|---|---|
| `backend/tests/test_tasks_api.py` | Routes and indexer, against both DynamoDB (moto) and the local store |
| `backend/tests/test_planner.py` | Tool loop, limits, validation, user isolation and prompt injection, with a fake model, plus real Converse request validation with botocore's Stubber |
| `backend/tests/test_local_server.py` | The real local server, with the smoke test pointed at it |
| `backend/tests/test_infra.py` | Templates against the agreed design |
| `backend/tests/test_scripts.py` | Deploy scripts run against a generated fake `aws` CLI placed first on `PATH`, and every CLI flag checked against the AWS service models |
| `backend/tests/test_iam.py` | Policy files, including that each person's script calls are allowed by their own policy |
| `backend/tests/test_docs.py` | Named files exist, decisions are complete, nothing secret is tracked |

The script tests need Bash, so they are skipped on Windows PowerShell. Run them in Git Bash or WSL.

On Node 18, `npm ci` prints `EBADENGINE` warnings from AWS SDK packages. These are expected, and the build still succeeds (D-024).

## Local modes

| Setting | Values | Default | Effect |
|---|---|---|---|
| `TASKCLOUD_STORE` | `local`, `dynamodb` | `local` when started by `local/server.py` | `local` keeps tasks in `local/.data/tasks.json`. Lambda always uses `dynamodb`. |
| `PLANNER_MODE` | `stub`, `bedrock` | `stub` | `stub` uses the scripted model in `local/stub_bedrock.py`, which works offline. `bedrock` calls real Bedrock. |
| `MODEL_ID` | A Bedrock model or profile ID | none | Required when `PLANNER_MODE=bedrock`. |
| `TASKCLOUD_DATA_DIR` | A folder | `local/.data` | Where local tasks and uploads live. |
| `PORT` | A port | `8787` | Port for the local server. |

Real Bedrock mode uses your own AWS profile, needs model access, and costs money:

```bash
PLANNER_MODE=bedrock MODEL_ID=apac.amazon.nova-lite-v1:0 AWS_PROFILE=<YOUR_PROFILE> AWS_REGION=ap-south-1 python3 local/server.py
```

This mode also needs boto3 installed. Stub mode does not.

To reset local data, stop the server and delete `local/.data`.

## Known differences from AWS

| Area | Local | AWS |
|---|---|---|
| Auth | Any bearer token is accepted and the user is always `local-user`. A missing token gets 401. | Cognito JWT verified by API Gateway. |
| Login screen | Skipped when `config.json` has `"mode": "local"`. | Real Cognito sign-in with the new-password step. |
| Store | One JSON file guarded by a lock. | DynamoDB. There is no difference between strong and eventual reads locally. |
| Uploads | Multipart POST to `/local/upload` on the local server. The same frontend code runs, because the response has the same `url` and `fields` shape as a pre-signed POST. The key is not signed and nothing expires. | Pre-signed POST direct to S3, enforced by the signed policy. |
| Indexer | Called directly by the server with a synthetic S3 event. | Invoked by the S3 event, asynchronously, so `attachmentKey` can appear a moment later. |
| Downloads | `/local/files/<key>`, no signature. | 5-minute pre-signed GET. |
| Planner | Scripted model that always makes a small generic plan from your prompt. | Real model. |
| Throttling | None. | Default burst 10, rate 5. `/plan` burst 2, rate 2. |
| Timeouts | None, though the planner still sees a simulated 28-second budget. | 28-second Lambda, 29-second integration. |
| CORS | The server allows localhost origins. | API Gateway allows all origins and handles preflight itself. Lambda sets no CORS headers. |

The server binds to `127.0.0.1` only, because it has no real authentication.
