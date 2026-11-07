# Decision log

Newest entries go at the bottom. D-001 to D-013 are the agreed seed decisions. Later entries are choices made during the build where the brief left room.

## D-001: Use region ap-south-1
- **Date:** 2026-11-07
- **Decision:** Deploy everything to Asia Pacific (Mumbai), `ap-south-1`.
- **Reason:** Lowest latency for students in Pune, and the India inference profile for Claude is available there.
- **Alternatives:** `ap-south-2` (Hyderabad), which has fewer services; `us-east-1`, which has more models but higher latency.
- **Files:** `scripts/lib/common.sh`, `infra/*.yaml`, `iam/policies/*`

## D-002: The planner is a Lambda agent loop on the Converse API
- **Date:** 2026-11-07
- **Decision:** The planner is a Lambda agent loop on the Bedrock Converse API with tools. Bedrock Agents is not used.
- **Reason:** Bedrock Agents is closed to new customers from 30 July 2026. A small loop is also simple to deploy with CloudFormation and to test with a fake client.
- **Alternatives:** Bedrock Agents (closed); a single prompt that returns JSON (not an agent, and weaker validation).
- **Files:** `backend/functions/planner_agent/handler.py`, `infra/3_agent.yaml`

## D-003: API Gateway with a Cognito JWT authorizer and public sign-up off
- **Date:** 2026-11-07
- **Decision:** Every route requires a Cognito JWT. Only an admin can create users.
- **Reason:** Protects Bedrock spending and keeps each student's data separate.
- **Alternatives:** Lambda function URLs (no built-in JWT check or route throttle); open sign-up (anyone could spend the budget).
- **Files:** `infra/1_data.yaml`, `infra/2_api.yaml`, `frontend/src/auth.js`

## D-004: Deploy from CloudShell using console users without access keys
- **Date:** 2026-11-07
- **Decision:** Team members log in to the console with MFA and run scripts in CloudShell.
- **Reason:** Nobody keeps long-lived keys on a laptop, and CloudShell has the tools already.
- **Alternatives:** Access keys on laptops (leak risk); a CI pipeline (more services than the project needs).
- **Files:** `docs/DEPLOYMENT.md`, `docs/IAM_ACL.md`, `scripts/*`

## D-005: Enforce the ACL with IAM. S3 ACLs stay disabled
- **Date:** 2026-11-07
- **Decision:** The course's access control list is implemented with IAM policies. Buckets use BucketOwnerEnforced.
- **Reason:** AWS recommends keeping S3 ACLs off, and there is no VPC, so no network ACL applies.
- **Alternatives:** S3 object ACLs (legacy, coarse); VPC network ACLs (no VPC).
- **Files:** `docs/IAM_ACL.md`, `iam/policies/*`, `infra/*.yaml`

## D-006: Claude Haiku 4.5 through the India inference profile
- **Date:** 2026-11-07
- **Decision:** Default model `in.anthropic.claude-haiku-4-5-20251001-v1:0`. The ID lives in SSM, so the app can switch to an Amazon Nova profile if Marketplace billing fails on the account.
- **Reason:** Low cost and fast. Claude on Bedrock is billed through Marketplace, which can fail on some Indian accounts, so a switch must not need a code change.
- **Alternatives:** Hard-coding the model (needs a redeploy to switch); Nova by default (Claude is the preferred first choice).
- **Files:** `infra/3_agent.yaml`, `scripts/lib/common.sh`, `backend/functions/planner_agent/handler.py`

## D-007: CORS allows all origins
- **Date:** 2026-11-07
- **Decision:** The API and the attachments bucket allow all origins.
- **Reason:** The Amplify URL is unknown until the last stack, and the app uses bearer tokens rather than cookies, so a foreign origin has no ambient credentials to abuse.
- **Alternatives:** Re-deploying the API stack with the Amplify URL after stack 4 (a circular deploy order).
- **Files:** `infra/2_api.yaml`

## D-008: Deploy the frontend through Amplify's CreateDeployment upload URL
- **Date:** 2026-11-07
- **Decision:** `scripts/4_frontend.sh` uploads a zip to the `zipUploadUrl` from `CreateDeployment`.
- **Reason:** Avoids Amplify's S3-bucket deployment option, which would need S3 ACLs on.
- **Alternatives:** Deploy from an S3 bucket (needs ACLs); Git-connected Amplify (needs a repository connection and build settings).
- **Files:** `scripts/4_frontend.sh`, `infra/4_frontend.yaml`

## D-009: 3_agent.sh applies the /plan throttle with update-stage
- **Date:** 2026-11-07
- **Decision:** The throttle (burst 2, rate 2) is set by `aws apigatewayv2 update-stage` after the agent stack deploys.
- **Reason:** CloudFormation rejects stage `RouteSettings` for a route key created in another stack. The script must be re-run after any API stack update.
- **Alternatives:** Moving `POST /plan` into the API stack (breaks stack ownership and the Aadesh/Aatyush split).
- **Files:** `scripts/3_agent.sh`, `docs/DEPLOYMENT.md`

## D-010: Add a download URL route and attachment cleanup
- **Date:** 2026-11-07
- **Decision:** Add `GET /tasks/{id}/attachment-url`, and delete the object in `DELETE /tasks/{id}`. `taskcloud-tasks-api-role` gains `s3:GetObject` and `s3:DeleteObject`. This is an addition to the PDF.
- **Reason:** Without it a student could upload a file but never open it, and deleted tasks would leave orphaned files that cost money.
- **Alternatives:** Public bucket reads (rejected, data must stay private).
- **Files:** `backend/functions/tasks_api/handler.py`, `infra/2_api.yaml`, `docs/IAM_ACL.md`

## D-011: Team members get read-only console access to their own services
- **Date:** 2026-11-07
- **Decision:** Each person can read the configuration of their own services for evidence screenshots, but never data.
- **Reason:** The evidence checklist needs screenshots. Data access is not needed for that.
- **Alternatives:** Aadesh takes every screenshot (does not show individual work).
- **Files:** `iam/policies/*`, `docs/IAM_ACL.md`

## D-012: Data resources use DeletionPolicy: Delete
- **Date:** 2026-11-07
- **Decision:** Data resources are deleted with their stacks, and `scripts/99_teardown.sh` removes everything.
- **Reason:** This is a course project, and leftovers would keep costing money after the demo.
- **Alternatives:** Retain (leaves resources to clean up by hand).
- **Files:** `infra/*.yaml`, `scripts/99_teardown.sh`

## D-013: The planner role allows any inference profile or foundation model
- **Date:** 2026-11-07
- **Decision:** `bedrock:InvokeModel` is allowed on `arn:aws:bedrock:*:<account>:inference-profile/*` and `arn:aws:bedrock:*::foundation-model/*`.
- **Reason:** The model can be switched by changing one parameter, with no IAM change. Inference profiles route across regions, so the region must be a wildcard.
- **Alternatives:** Naming one model (the Nova fallback would need a stack update).
- **Files:** `infra/3_agent.yaml`, `docs/IAM_ACL.md`

## D-014: POST /tasks and PATCH /tasks/{id} reject unknown fields
- **Date:** 2026-11-07
- **Decision:** A body with any field outside the allowed list gets a 400. `POST /tasks` requires `title` and `dueDate`, with `priority` defaulting to `medium` and `estMinutes` to 30.
- **Reason:** The brief says updates cover allowed fields only. Rejecting loudly surfaces client bugs, and makes it obvious that `userId`, `source` and `attachmentKey` can never be set by a caller.
- **Alternatives:** Silently ignoring unknown fields (hides mistakes).
- **Files:** `backend/shared/validation.py`, `backend/functions/tasks_api/handler.py`

## D-015: One attachment per task, with 409 on a second upload
- **Date:** 2026-11-07
- **Decision:** `POST /tasks/{id}/attachment-url` returns 409 if the task already has an attachment.
- **Reason:** `DELETE /tasks/{id}` only knows the current `attachmentKey`, and the tasks role has no `s3:ListBucket`, so replacing a file under a new name would orphan the old object. This also gives 409 a clear meaning.
- **Alternatives:** Replacing in place (orphans objects, or deletes the old file before the new upload succeeds); a delete-attachment route (not in the agreed design).
- **Limit:** To change a file, delete the task and create it again.
- **Files:** `backend/functions/tasks_api/handler.py`, `frontend/src/components/TaskItem.jsx`

## D-016: The streak survives until the IST day ends
- **Date:** 2026-11-07
- **Decision:** `streakDays` counts back from today, or from yesterday if nothing has been completed yet today.
- **Reason:** Otherwise a student's streak would show 0 every morning until their first completed task.
- **Alternatives:** Always counting from today (discouraging and misleading).
- **Files:** `backend/shared/progress.py`

## D-017: Downloads open inline only for an allow-list of safe types
- **Date:** 2026-11-07
- **Decision:** The pre-signed GET sets the response content type from the file extension for PDF, PNG, JPEG, GIF, WebP and plain text, with `inline` disposition. Anything else is sent as `application/octet-stream` with `attachment` disposition.
- **Reason:** Uploads post no content type, so S3 would serve everything as binary and the "open" button would always download. An allow-list opens study notes in the browser without ever rendering uploaded HTML or SVG.
- **Alternatives:** Trusting a client-supplied content type (lets an uploader serve active content).
- **Files:** `backend/shared/attachments.py`

## D-018: get_open_tasks returns at most 100 tasks
- **Date:** 2026-11-07
- **Decision:** The tool returns the 100 soonest-due todo tasks.
- **Reason:** A long task list becomes model input on every later call, which would spend the budget without improving the plan.
- **Alternatives:** Returning all 500 (costly); no cap (unbounded input tokens).
- **Files:** `backend/functions/planner_agent/handler.py`

## D-019: The deploy role cannot scope every action by name
- **Date:** 2026-11-07
- **Decision:** `taskcloud-cfn-role` is scoped by the `taskcloud-` prefix wherever a service allows it. Lambda log groups use `/aws/lambda/taskcloud-*`. Cognito user pools, HTTP APIs and Amplify apps are scoped by service and region only. The role has an explicit Deny on changing itself.
- **Reason:** Those three services give resources generated IDs, so their ARNs have no name to match. Lambda writes to `/aws/lambda/<function>` by default, so that path is the natural log group name. The Deny is needed because the role's own name matches the `taskcloud-*` pattern it manages.
- **Alternatives:** Custom log group names (more configuration for no benefit); `*` on all actions (far too broad).
- **Files:** `infra/0_foundation.yaml`, `docs/IAM_ACL.md`

## D-020: amplify:ListApps is granted on all resources
- **Date:** 2026-11-07
- **Decision:** Krushna's `ListApps` permission is a separate statement on `*`, while the other Amplify actions are on `apps/*` as agreed.
- **Reason:** `ListApps` is not an action on a specific app, so `apps/*` may not match it. It exposes only app metadata in this account, and the Amplify console needs it.
- **Alternatives:** Leaving it on `apps/*` (the console list could fail).
- **Files:** `iam/policies/user-krushna.json`, `docs/IAM_ACL.md`

## D-021: Lambda Code paths suppress one cfn-lint warning
- **Date:** 2026-11-07
- **Decision:** Each `AWS::Lambda::Function` suppresses cfn-lint W3002 through resource metadata.
- **Reason:** W3002 warns that a local `Code` path only works with `aws cloudformation package`. That is the agreed way to package, so the warning is expected. Suppressing it per resource keeps every other check active.
- **Alternatives:** Ignoring W3002 across the project (could hide a real mistake elsewhere); S3 parameters instead of a path (the brief specifies the path).
- **Files:** `infra/2_api.yaml`, `infra/3_agent.yaml`

## D-022: Audit trail covers all regions and expires logs after 90 days
- **Date:** 2026-11-07
- **Decision:** `taskcloud-trail` is multi-region, and its bucket expires objects after 90 days.
- **Reason:** A deploy role or stolen session could act in any region, so a Mumbai-only trail would miss it. The first copy of management events is free, so only storage costs money, and 90 days covers the course.
- **Alternatives:** A single-region trail (blind to other regions and to global service events).
- **Files:** `infra/0_foundation.yaml`

## D-023: A few small files beyond the listed layout
- **Date:** 2026-11-07
- **Decision:** Add `pyproject.toml` (pytest and ruff settings), `.gitattributes` (LF line endings), `local/stub_bedrock.py` (the scripted model), `backend/shared/attachments.py`, `backend/shared/progress.py`, `backend/shared/timeutil.py`, `frontend/config.local.example.json` and `frontend/scripts/ensure-config.mjs`.
- **Reason:** `frontend/public/config.json` must stay git-ignored, so a fresh clone needs another way to get a local config. Team members use Windows, where CRLF line endings would break Bash in CloudShell. The rest keeps each file to one job.
- **Alternatives:** Committing a config file (breaks the no-generated-config rule); one large `server.py` or shared module.
- **Files:** as listed

## D-024: Node 18 builds, with engine warnings from a dependency
- **Date:** 2026-11-07
- **Decision:** Keep `aws-amplify` 6.22.2 and Vite 5.4.21. `npm ci` on Node 18 prints `EBADENGINE` warnings, because some AWS SDK packages inside Amplify declare Node 20 or later. The warnings are not errors, and the build succeeds on Node 18 and 20.
- **Reason:** These packages run in the browser bundle, not on Node, so the declared Node version does not affect the running site. Vite 5 is the newest major that supports Node 18.
- **Alternatives:** An older Amplify release (misses fixes, and could still warn); dropping Node 18 (the brief requires it).
- **Files:** `frontend/package.json`, `frontend/package-lock.json`

## D-025: A re-run of 3_agent.sh keeps the current model
- **Date:** 2026-11-07
- **Decision:** `scripts/3_agent.sh` reads `/taskcloud/modelId` and passes it back as the `ModelId` parameter, unless a `MODEL_ID` environment variable overrides it.
- **Reason:** The script must be re-run after API updates. Otherwise each re-run would silently revert a switch to Nova, back to a model the account may not be able to pay for.
- **Alternatives:** Always using the template default (the silent revert described).
- **Files:** `scripts/3_agent.sh`, `docs/DEPLOYMENT.md`

## D-026: Fonts load from Google Fonts, with system fallbacks
- **Date:** 2026-11-07
- **Decision:** `frontend/index.html` loads Kalam (headings and margin dates) and Atkinson Hyperlegible (everything else) from Google Fonts.
- **Reason:** Plain CSS with no UI library or font package. If the fonts are blocked or offline, the page still works with system fonts.
- **Alternatives:** Bundling font files (adds weight to the repo); system fonts only (loses the exercise-book character).
- **Files:** `frontend/index.html`, `frontend/src/styles.css`

## D-027: GET /progress reads up to 5000 tasks
- **Date:** 2026-11-07
- **Decision:** `GET /tasks` stops at 500 as agreed, but `GET /progress` reads up to 5000.
- **Reason:** With the same cap, totals and streaks would silently go wrong for anyone past 500 tasks. 5000 is far beyond a course's use and still bounds the work of one request.
- **Alternatives:** No cap (unbounded read inside a 10-second Lambda).
- **Files:** `backend/functions/tasks_api/handler.py`

## D-028: The frontend is a kawaii stationery journal with a mascot
- **Date:** 2026-11-07
- **Decision:** Replace the ruled-notebook look with dotted journal paper, washi tape and sticker-style tasks in a pastel palette, and add the mascot Mochi. The fonts become Mochiy Pop One and M PLUS Rounded 1c, which replaces the font choice in D-026. Mochi says short random phrases, reacts to events, and opens the AI planner as a pop-up bubble.
- **Reason:** Requested by the team. Putting the planner behind the mascot gives the mascot a job and keeps the page uncluttered. The planner stays mounted while closed, so a running plan is not lost. Only real events are announced to screen readers, because idle chatter would be noise. All motion is off under `prefers-reduced-motion`.
- **Alternatives:** A separate AI button beside a purely decorative mascot (two corner widgets for one idea); an always-visible planner box (takes the top of the page).
- **Files:** `frontend/src/styles.css`, `frontend/src/components/Mascot.jsx`, `frontend/src/components/MochiFace.jsx`, `frontend/src/components/PlannerBox.jsx`, `frontend/src/data/phrases.js`, `frontend/index.html`

## D-029: Daily quotes are original and unattributed
- **Date:** 2026-11-07
- **Decision:** `frontend/src/data/quotes.js` holds 80 lines written for TaskCloud. A fixed seeded shuffle plus the IST date picks one, so it looks random, stays the same all day, and repeats only after all 80 have been used.
- **Reason:** Famous quotes are often misattributed, and some are under copyright. A plain random pick per day could repeat on consecutive days.
- **Alternatives:** A quotes API (a new service and a network dependency); famous quotes (attribution risk).
- **Files:** `frontend/src/data/quotes.js`, `frontend/src/components/QuoteCard.jsx`, `backend/tests/test_frontend_content.py`

## D-030: Calendar, filters and focus timer run entirely in the browser
- **Date:** 2026-11-07
- **Decision:** Add a month calendar with a day panel, filter chips and search, a today ring, confetti on completing a task, and a 25-minute focus timer with a 5-minute rest. None of them adds a route, field or service. The calendar places tasks by `dueDate`. The chosen view is kept in `localStorage`, wrapped so that a blocked browser store is harmless.
- **Reason:** All of it can be worked out from `GET /tasks` and `GET /progress`, so the agreed API, data model and IAM stay as they are.
- **Alternatives:** Saving focus sessions on the server (needs a new route and data).
- **Limit:** The timer's state is lost if the page reloads, and the calendar only shows the tasks `GET /tasks` returns, which is up to 500.
- **Files:** `frontend/src/components/CalendarView.jsx`, `frontend/src/components/FocusTimer.jsx`, `frontend/src/components/Dashboard.jsx`, `frontend/src/components/Confetti.jsx`, `frontend/src/components/AddTask.jsx`

