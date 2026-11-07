# TaskCloud

TaskCloud is a serverless student productivity app, built as the course project for DS3203A Cloud Computing at VIT Pune. Students manage daily tasks in a list or calendar, track their progress and streaks, attach study files, and turn one typed prompt into a saved study plan using an AI agent. The app looks like a blue kawaii stationery journal that works well on phones, with a daily note, a focus timer, and Mochi, a round mascot who opens the planner.

## Architecture summary

A React single-page app on AWS Amplify Hosting signs students in through Amazon Cognito (public sign-up is off) and calls an API Gateway HTTP API with a JWT. Three Python Lambda functions do the work:

- `taskcloud-tasks-api` handles task operations and progress, stored in the DynamoDB table `taskcloud-tasks`.
- `taskcloud-attachment-indexer` links a file to its task when S3 reports a new upload.
- `taskcloud-planner-agent` runs an agent loop on the Amazon Bedrock Converse API. The model chooses a tool, and Lambda validates and carries out the call.

Five CloudFormation stacks create everything. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Team

| Person | IAM user | Stack | Script |
|---|---|---|---|
| Aadesh (admin) | `aadesh-admin` | `taskcloud-foundation`, `taskcloud-agent` | `scripts/0_foundation.sh`, `scripts/3_agent.sh` |
| Sanchit | `sanchit` | `taskcloud-data` | `scripts/1_data.sh` |
| Aatyush | `aatyush` | `taskcloud-api` | `scripts/2_api.sh` |
| Krushna | `krushna` | `taskcloud-frontend` | `scripts/4_frontend.sh` |

## Local quick start

You need Python 3.11 or later and Node 18 or later. No AWS account is needed. The local server uses only the Python standard library and a scripted stand-in for the AI model.

### Windows PowerShell

```powershell
# Terminal 1: API on http://localhost:8787
python local\server.py

# Terminal 2: app on http://localhost:5173
cd frontend
npm ci
npm run dev
```

### Linux or macOS

```bash
# Terminal 1: API on http://localhost:8787
python3 local/server.py

# Terminal 2: app on http://localhost:5173
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Local mode skips login and uses the fixed user `local-user`. See [docs/LOCAL_DEV.md](docs/LOCAL_DEV.md) for tests and modes.

## Deploying to AWS

Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Each person runs one script from AWS CloudShell, in stack order. Access control is described in [docs/IAM_ACL.md](docs/IAM_ACL.md).

## Project tracking

- [docs/TILLNOW.md](docs/TILLNOW.md): current progress and next step.
- [docs/DECISIONS.md](docs/DECISIONS.md): why the design is the way it is.
- [docs/TaskCloud_Cloud_Architecture.pdf](docs/TaskCloud_Cloud_Architecture.pdf): the original architecture and deployment plan.
