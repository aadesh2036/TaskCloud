# Deployment runbook

Everyone deploys from AWS CloudShell in `ap-south-1` (Mumbai), one script each, in order. No access keys are involved (D-004).

**The golden rule: if a script fails, do not fix it in the console.** The live setup would no longer match the code. Send the log file to Aadesh, wait for the fix, then run the same script again. Every script is safe to re-run.

## Deploy order

| Order | Person | Script | Stack |
|---|---|---|---|
| Before anyone | Aadesh | Pre-flight checks below | |
| 0 | Aadesh | `scripts/0_foundation.sh` | `taskcloud-foundation` |
| | Aadesh | Create users and group (`docs/IAM_ACL.md`) | |
| 1 | Sanchit | `scripts/1_data.sh` | `taskcloud-data` |
| 2 | Aatyush | `scripts/2_api.sh` | `taskcloud-api` |
| 3 | Aadesh | `scripts/3_agent.sh` | `taskcloud-agent` |
| 4 | Krushna | `scripts/4_frontend.sh` | `taskcloud-frontend` |
| Last | Aadesh | `scripts/create_demo_user.sh` | |

## Getting the code into CloudShell

Aadesh shares the code through a Git repository or a zip file. In the CloudShell terminal:

```bash
# From Git (use your repository URL)
git clone <REPOSITORY_URL> ~/taskcloud

# Or from a zip uploaded with Actions > Upload file
unzip taskcloud.zip -d ~/taskcloud

cd ~/taskcloud
```

Then run your script with `bash scripts/<your_script>.sh`. Using `bash` works whether or not the zip kept the executable bit.

## Aadesh: pre-flight checks

1. Turn on MFA for the root user, then work as `aadesh-admin` rather than root.
2. Add a valid payment method. In Bedrock, submit Anthropic's use-case details and test the model once in the playground from Mumbai.

**Billing risk:** Claude on Bedrock is billed through AWS Marketplace, so promotional credits may not cover it, and Indian (AISPL) accounts have reported payment errors when subscribing. The model check in `scripts/0_foundation.sh` tells you whether this account can call the model. If it fails, see "Switching to Amazon Nova" below.

## What each script does

Every deploy script prints who is running it and the region, checks prerequisite stacks, deploys, prints the stack status, last 20 events and outputs, and saves everything to `logs/<script>_<YYYYMMDD-HHMMSS>.log`.

### 0. `scripts/0_foundation.sh` (Aadesh)

```bash
bash scripts/0_foundation.sh <ALERT_EMAIL> 5
```

Runs as `aadesh-admin`, without the deploy role, because it creates that role. Takes the budget alert email and the US$ limit. Afterwards:

- It lists the active inference profiles in `ap-south-1`.
- It sends one test message to the configured model. If this fails the script warns but does not stop, because the fallback is a parameter change.
- **Confirm the AWS Budgets subscription email** if one arrives, and then create the users (`docs/IAM_ACL.md`).

### 1. `scripts/1_data.sh` (Sanchit)

```bash
bash scripts/1_data.sh
```

Deploys the table and user pool, then prints the table status and user pool name as evidence.

### 2. `scripts/2_api.sh` (Aatyush)

```bash
bash scripts/2_api.sh
```

Builds the Lambdas with `scripts/build_lambdas.sh`, packages them into the artifact bucket and deploys. Then it calls `GET /tasks` with curl and no token, and shows the 401.

### 3. `scripts/3_agent.sh` (Aadesh)

```bash
bash scripts/3_agent.sh
```

Packages and deploys the agent stack, applies the `/plan` throttle with `update-stage` (D-009), and prints an end-to-end test command.

**Re-run this script after any API stack update**, because an API stack update can reset the route throttle.

### 4. `scripts/4_frontend.sh` (Krushna)

```bash
bash scripts/4_frontend.sh
```

Needs no decisions from you. It checks Node is 18 or later, deploys the frontend stack, reads the IDs from the data, API and frontend stacks, runs `npm ci` and `npm run build`, writes `dist/config.json`, zips the contents of `dist/`, uploads the zip with `create-deployment` and curl, starts the deployment, waits for it, and prints the site URL.

### Demo user (Aadesh)

```bash
bash scripts/create_demo_user.sh <DEMO_EMAIL>
```

Creates a confirmed user with the welcome message suppressed. It prompts for the password, so it never appears in the log or shell history. The password must have at least 8 characters with upper case, lower case and a number.

### End-to-end test (Aadesh)

`scripts/3_agent.sh` prints the commands, which are:

1. Get a token by logging in to the site and copying it from the browser, or use the site directly.
2. `POST /plan` with the prompt "DBMS exam on Friday, finish my lab record, and revise two hours a day."
3. Check that new tasks appear on the dashboard with an AI badge.

## Switching to Amazon Nova

Aadesh runs this, with no redeploy. Containers cache the value, so also force a new container by updating the function's description:

```bash
aws ssm put-parameter --name /taskcloud/modelId --type String --overwrite \
  --value apac.amazon.nova-lite-v1:0 --region ap-south-1
aws lambda update-function-configuration --function-name taskcloud-planner-agent \
  --description "model switched" --region ap-south-1
```

Confirm the exact Nova profile ID with `aws bedrock list-inference-profiles --region ap-south-1` first, because the ID above is only an example. A later `scripts/3_agent.sh` run reads the current parameter and keeps it, so it will not undo the switch.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| "Prerequisite stack ... is not ready" | An earlier person has not finished | Wait for them, then re-run |
| "is in ROLLBACK_COMPLETE state" | The first create of the stack failed | Send the log to Aadesh, who reads the events, deletes the stack and fixes the cause. Team users cannot delete stacks. Then re-run. |
| `AccessDenied` on `iam:PassRole` | The user is not in `TaskCloud-Deployers`, or `iam/rendered` was not applied | Send the log to Aadesh |
| `AccessDenied` for a resource inside the events | `taskcloud-cfn-role` is missing an action | Send the log to Aadesh, who adds it in `infra/0_foundation.yaml` and re-runs script 0 |
| `No export named taskcloud-...` | A prerequisite stack is missing or old | Re-run the earlier script |
| Export cannot be updated because it is in use | A template change renames an export another stack imports | Aadesh deletes the importing stack first |
| Planner returns 500, logs show `AccessDeniedException` | Model access or Marketplace subscription is missing | Aadesh re-tests in the playground, or switches to Nova |
| `/plan` returns 503 | The Lambda hit its 28-second limit | Try a shorter prompt. Saved tasks stay saved. |
| Browser CORS error on upload | Bucket CORS is missing | Re-run `scripts/2_api.sh` |
| Upload succeeds but no file shows | The indexer did not run | Check `/aws/lambda/taskcloud-attachment-indexer` in CloudWatch |
| Site shows old content | Browser cache | Hard refresh. Check the job in the Amplify console. |
| CloudShell lost files | CloudShell deletes home data after 120 days without use | Clone or unzip again. Logs you need should be downloaded soon after running. |
| `/plan` throttle missing after an API update | Stage route settings were reset | Re-run `scripts/3_agent.sh` |

## Teardown (Aadesh)

```bash
bash scripts/99_teardown.sh
```

It asks you to type `DELETE`, stops CloudTrail logging, empties the S3 buckets, then deletes stacks 4 to 0 in order, waiting for each (D-012). It is safe to re-run if interrupted. Afterwards delete the IAM users, group and policy by hand (`docs/IAM_ACL.md`), and check **AWS Budgets** and **Billing** a day later.

## Evidence checklist

Everyone also submits their log file, using CloudShell's **Actions > Download file**, from `logs/`.

### Aadesh
- [ ] Screenshots: IAM users and group, MFA enabled, permission policies, budget, CloudTrail trail, Bedrock playground.
- [ ] `taskcloud-foundation` and `taskcloud-agent` showing `CREATE_COMPLETE`.
- [ ] Test: `POST /plan` creates tasks that appear in DynamoDB.
- [ ] Logs: `0_foundation_*.log`, `3_agent_*.log`.

### Sanchit
- [ ] Screenshots: terminal with script output, `taskcloud-data` `CREATE_COMPLETE` and its Events tab, DynamoDB table settings, Cognito user pool.
- [ ] Test: the `describe-table` output in the script shows the table as `ACTIVE`.
- [ ] Log: `1_data_*.log`.

### Aatyush
- [ ] Screenshots: terminal with script output, `taskcloud-api` `CREATE_COMPLETE`, API routes and authorizer, Lambda list, S3 event notification.
- [ ] Test: a call without a token returns 401; an uploaded file triggers the Lambda.
- [ ] Log: `2_api_*.log`.

### Krushna
- [ ] Screenshots: terminal with script output, `taskcloud-frontend` `CREATE_COMPLETE`, Amplify app showing a successful deployment.
- [ ] Test: the live Amplify URL opens the login page.
- [ ] Log: `4_frontend_*.log`.
