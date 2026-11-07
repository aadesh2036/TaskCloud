# Access control (IAM-based ACL)

S3 object ACLs stay disabled and there is no VPC, so there are no network ACLs. IAM enforces all access (D-005). The policy files are in `iam/policies/`. They use the `<ACCOUNT_ID>` placeholder, which `scripts/render_iam.sh` fills into `iam/rendered/` (git-ignored).

## Access matrix

| Action | Aadesh (`aadesh-admin`) | Sanchit (`sanchit`) | Aatyush (`aatyush`) | Krushna (`krushna`) |
|---|---|---|---|---|
| Billing, budgets, IAM users and policies | Full | None | None | None |
| Bedrock playground and model setup | Full | None | None | None |
| Use AWS CloudShell | Yes | Yes | Yes | Yes |
| View CloudFormation stacks, events and exports | Full | Read | Read | Read |
| Pass `taskcloud-cfn-role` to CloudFormation | Yes | Yes | Yes | Yes |
| Deploy `taskcloud-foundation` | Yes | None | None | None |
| Deploy `taskcloud-data` | Yes | Deploy | None | None |
| Deploy `taskcloud-api` | Yes | None | Deploy | None |
| Deploy `taskcloud-agent` | Yes | None | None | None |
| Deploy `taskcloud-frontend` | Yes | None | None | Deploy |
| Delete any stack | Yes | None | None | None |
| Upload Lambda code to the artifact bucket | Yes | None | Upload | None |
| Create and start Amplify deployments | Yes | None | None | Deploy |
| Read DynamoDB table metadata | Yes | Read | None | None |
| Read Cognito pool settings | Yes | Read | None | None |
| Read API Gateway and Lambda configuration | Yes | None | Read | None |
| Read attachments bucket notification settings | Yes | None | Read | None |
| Read Amplify apps, branches and jobs | Yes | None | None | Read |
| Read or write task items in DynamoDB | Yes | None | None | None |
| Read or write attachment objects in S3 | Yes | None | None | None |
| Invoke Bedrock | Yes | None | None | None |
| Create demo users | Yes | None | None | None |

## Group: TaskCloud-Deployers

Members: `sanchit`, `aatyush`, `krushna`.

- AWS managed policy `AWSCloudShellFullAccess`.
- Customer policy `TaskCloud-Deployers`, from `iam/policies/group-deployers.json`:
  - `sts:GetCallerIdentity`.
  - CloudFormation `Describe*`, `List*`, `Get*` and `ValidateTemplate`.
  - `iam:PassRole` on `taskcloud-cfn-role` only, with the condition `iam:PassedToService = cloudformation.amazonaws.com`.

## Inline policies

Each is scoped to the person's stack ARN, `arn:aws:cloudformation:ap-south-1:<ACCOUNT_ID>:stack/<stack-name>/*`, and grants what `aws cloudformation deploy` needs: `CreateStack`, `UpdateStack`, `CreateChangeSet`, `DescribeChangeSet`, `ExecuteChangeSet`, `DeleteChangeSet`, `DescribeStacks`, `DescribeStackEvents` and `GetTemplateSummary`.

| User | File | Adds |
|---|---|---|
| `sanchit` | `iam/policies/user-sanchit.json` | Read-only Describe and List on the table metadata and Cognito pool |
| `aatyush` | `iam/policies/user-aatyush.json` | `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on the artifact bucket; read-only Describe, List and Get on API Gateway, Lambda configuration and the attachments bucket's notification settings; `s3:ListAllMyBuckets` so the S3 console opens (bucket names only, no objects) |
| `krushna` | `iam/policies/user-krushna.json` | Amplify `CreateDeployment`, `StartDeployment`, `GetJob`, `ListJobs`, `GetApp`, `GetBranch` on `apps/*`, and `ListApps` (D-020) |

No team member gets data access: no DynamoDB item reads or writes, no attachment objects, no Bedrock, no IAM and no billing.

## Service roles

Defined in the CloudFormation templates, not in `iam/policies/`.

| Role | Used by | Allowed actions |
|---|---|---|
| `taskcloud-cfn-role` | CloudFormation | Create, update and delete `taskcloud-*` resources of the listed services. Denied any change to itself. See the notes below. |
| `taskcloud-tasks-api-role` | `taskcloud-tasks-api` | `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Query` on the table; `s3:PutObject`, `GetObject`, `DeleteObject` on the attachments bucket; write logs |
| `taskcloud-indexer-role` | `taskcloud-attachment-indexer` | `dynamodb:UpdateItem` on the table; write logs |
| `taskcloud-planner-role` | `taskcloud-planner-agent` | `bedrock:InvokeModel` on `arn:aws:bedrock:*:<ACCOUNT_ID>:inference-profile/*` and `arn:aws:bedrock:*::foundation-model/*`; `ssm:GetParameter` on `/taskcloud/modelId`; `dynamodb:Query`, `PutItem`, `BatchWriteItem` on the table; write logs |

Notes on `taskcloud-cfn-role`:

- Names are scoped by the `taskcloud-` prefix wherever the service allows it. Lambda log groups use `/aws/lambda/taskcloud-*` (D-019).
- Cognito user pools, HTTP APIs and Amplify apps get generated IDs, so those actions cannot be scoped by name. They are scoped to the service and region instead (D-019).
- It can read objects in the artifact bucket, because Lambda fetches the code zip with the caller's permissions.
- It can only pass `taskcloud-*-role` roles, and only to Lambda.

## Known limit

Anyone who can pass the deploy role could use it, through their own stack, to create other allowed resources. That is acceptable for a trusted team of four, and CloudTrail records it. Delete the users after the project.

## Console steps for Aadesh

Do these after `scripts/0_foundation.sh` has created `taskcloud-cfn-role` and the artifact bucket, signed in as `aadesh-admin`. That user is created beforehand from the root account, with MFA and the AWS managed policy `AdministratorAccess`, and is then the only admin used.

1. In CloudShell, run `./scripts/render_iam.sh`. Then open each file in `iam/rendered/`, for example `cat iam/rendered/group-deployers.json`, to copy it.
2. Open **IAM > Policies > Create policy > JSON**. Paste `iam/rendered/group-deployers.json`, name it `TaskCloud-Deployers`, and create it.
3. Open **IAM > User groups > Create group**. Name it `TaskCloud-Deployers`.
4. Attach `AWSCloudShellFullAccess` and `TaskCloud-Deployers` to the group, and create it.
5. Open **IAM > Users > Create user**. Enter `sanchit` and tick **Provide user access to the AWS Management Console**. Choose **I want to create an IAM user**, set a custom password, and require a password reset at next sign-in.
6. On the permissions page, choose **Add user to group** and pick `TaskCloud-Deployers`. Create the user. **Do not create access keys.**
7. Open the user, then **Permissions > Add permissions > Create inline policy > JSON**. Paste `iam/rendered/user-sanchit.json` and name it `taskcloud-sanchit`.
8. Repeat steps 5 to 7 for `aatyush` with `iam/rendered/user-aatyush.json` and `krushna` with `iam/rendered/user-krushna.json`.
9. Have each person sign in, change their password, and register an MFA device under **Security credentials**. Confirm each has MFA under **IAM > Users**.
10. Check each user under **Security credentials**: the **Access keys** section must be empty.
11. After the project, delete all three users and the group and policy.
