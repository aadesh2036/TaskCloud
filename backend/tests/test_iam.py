"""Checks the IAM policy files, including that each person's script can do what it needs."""

import fnmatch
import json
import subprocess
from pathlib import Path

import pytest
from test_scripts import needs_bash, sandbox  # noqa: F401 - pytest finds the fixture by name

REPO = Path(__file__).resolve().parents[2]
POLICIES = REPO / "iam" / "policies"
GROUP = json.loads((POLICIES / "group-deployers.json").read_text(encoding="utf-8"))
USERS = {
    name: json.loads((POLICIES / f"user-{name}.json").read_text(encoding="utf-8"))
    for name in ("sanchit", "aatyush", "krushna")
}
ACCOUNT = "<ACCOUNT_ID>"
REGION = "ap-south-1"
STACKS = {"sanchit": "taskcloud-data", "aatyush": "taskcloud-api", "krushna": "taskcloud-frontend"}
ARTIFACTS = f"arn:aws:s3:::taskcloud-artifacts-{ACCOUNT}-{REGION}"


def as_list(value):
    return value if isinstance(value, list) else [value]


def statements(policy):
    return policy["Statement"]


def allowed(policies, action, resource):
    """A small IAM evaluator: Allow statements only, wildcards in actions and resources."""
    for policy in policies:
        for statement in statements(policy):
            if statement["Effect"] != "Allow":
                continue
            if any(fnmatch.fnmatchcase(action, a) for a in as_list(statement["Action"])) and any(
                fnmatch.fnmatchcase(resource, r) for r in as_list(statement["Resource"])
            ):
                return True
    return False


def actions_of(policy):
    return {a for s in statements(policy) for a in as_list(s["Action"])}


def stack_arn(stack):
    return f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{stack}/id"


def test_policy_files_are_exactly_these():
    assert {p.name for p in POLICIES.glob("*.json")} == {
        "group-deployers.json", "user-sanchit.json", "user-aatyush.json", "user-krushna.json",
    }


def test_files_use_placeholder_and_no_real_account_ids():
    import re

    for path in POLICIES.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b\d{12}\b", text), path.name
    assert all(ACCOUNT in json.dumps(user) for user in USERS.values())


def test_group_policy():
    assert allowed([GROUP], "sts:GetCallerIdentity", "*")
    for action in ("cloudformation:DescribeStacks", "cloudformation:ListExports", "cloudformation:GetTemplate",
                   "cloudformation:ValidateTemplate"):
        assert allowed([GROUP], action, "*")
    assert not allowed([GROUP], "cloudformation:CreateStack", "*")
    assert not allowed([GROUP], "cloudformation:DeleteStack", "*")

    passing = next(s for s in statements(GROUP) if s["Action"] == "iam:PassRole")
    assert passing["Resource"] == f"arn:aws:iam::{ACCOUNT}:role/taskcloud-cfn-role"
    assert passing["Condition"] == {"StringEquals": {"iam:PassedToService": "cloudformation.amazonaws.com"}}


@pytest.mark.parametrize("name", STACKS)
def test_each_user_can_deploy_only_their_own_stack(name):
    needed = ["CreateStack", "UpdateStack", "CreateChangeSet", "DescribeChangeSet", "ExecuteChangeSet",
              "DeleteChangeSet", "DescribeStacks", "DescribeStackEvents", "GetTemplateSummary"]
    all_stacks = ["taskcloud-foundation", "taskcloud-data", "taskcloud-api", "taskcloud-agent", "taskcloud-frontend"]
    for action in needed:
        for stack in all_stacks:
            assert allowed([USERS[name]], f"cloudformation:{action}", stack_arn(stack)) == (stack == STACKS[name])


@pytest.mark.parametrize("name", STACKS)
def test_nobody_on_the_team_can_delete_a_stack(name):
    assert not allowed([GROUP, USERS[name]], "cloudformation:DeleteStack", stack_arn(STACKS[name]))


DATA_ACTIONS = [
    ("dynamodb:GetItem", "arn:aws:dynamodb:ap-south-1:<ACCOUNT_ID>:table/taskcloud-tasks"),
    ("dynamodb:Query", "arn:aws:dynamodb:ap-south-1:<ACCOUNT_ID>:table/taskcloud-tasks"),
    ("dynamodb:Scan", "arn:aws:dynamodb:ap-south-1:<ACCOUNT_ID>:table/taskcloud-tasks"),
    ("dynamodb:PutItem", "arn:aws:dynamodb:ap-south-1:<ACCOUNT_ID>:table/taskcloud-tasks"),
    ("dynamodb:DeleteTable", "arn:aws:dynamodb:ap-south-1:<ACCOUNT_ID>:table/taskcloud-tasks"),
    ("s3:GetObject", "arn:aws:s3:::taskcloud-attachments-<ACCOUNT_ID>-ap-south-1/user/task/file"),
    ("s3:PutObject", "arn:aws:s3:::taskcloud-attachments-<ACCOUNT_ID>-ap-south-1/user/task/file"),
    ("s3:DeleteObject", "arn:aws:s3:::taskcloud-attachments-<ACCOUNT_ID>-ap-south-1/user/task/file"),
    ("s3:ListBucket", "arn:aws:s3:::taskcloud-attachments-<ACCOUNT_ID>-ap-south-1"),
    ("bedrock:InvokeModel", "arn:aws:bedrock:ap-south-1::foundation-model/any"),
    ("iam:CreateRole", "arn:aws:iam::<ACCOUNT_ID>:role/taskcloud-x"),
    ("iam:PutRolePolicy", "arn:aws:iam::<ACCOUNT_ID>:role/taskcloud-cfn-role"),
    ("cognito-idp:AdminCreateUser", "arn:aws:cognito-idp:ap-south-1:<ACCOUNT_ID>:userpool/x"),
    ("cognito-idp:ListUsers", "arn:aws:cognito-idp:ap-south-1:<ACCOUNT_ID>:userpool/x"),
    ("budgets:ViewBudget", "*"),
    ("ce:GetCostAndUsage", "*"),
    ("aws-portal:ViewBilling", "*"),
    ("ssm:PutParameter", "arn:aws:ssm:ap-south-1:<ACCOUNT_ID>:parameter/taskcloud/modelId"),
    ("lambda:UpdateFunctionCode", "arn:aws:lambda:ap-south-1:<ACCOUNT_ID>:function:taskcloud-tasks-api"),
    ("lambda:InvokeFunction", "arn:aws:lambda:ap-south-1:<ACCOUNT_ID>:function:taskcloud-tasks-api"),
]


@pytest.mark.parametrize("name", STACKS)
@pytest.mark.parametrize("action, resource", DATA_ACTIONS)
def test_no_team_member_has_data_or_admin_access(name, action, resource):
    assert not allowed([GROUP, USERS[name]], action, resource)


def test_only_aatyush_can_upload_lambda_code():
    obj = f"{ARTIFACTS}/lambda/abc"
    assert allowed([USERS["aatyush"]], "s3:PutObject", obj)
    assert not allowed([USERS["sanchit"]], "s3:PutObject", obj)
    assert not allowed([USERS["krushna"]], "s3:PutObject", obj)


def test_only_krushna_can_deploy_the_site():
    app = f"arn:aws:amplify:{REGION}:{ACCOUNT}:apps/abc/branches/main"
    assert allowed([USERS["krushna"]], "amplify:CreateDeployment", app)
    assert not allowed([USERS["aatyush"]], "amplify:CreateDeployment", app)
    assert not allowed([USERS["sanchit"]], "amplify:CreateDeployment", app)


def test_read_access_matches_each_persons_own_services():
    assert allowed([USERS["sanchit"]], "dynamodb:DescribeTable", f"arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/taskcloud-tasks")
    assert not allowed([USERS["aatyush"]], "dynamodb:DescribeTable", f"arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/taskcloud-tasks")
    assert allowed([USERS["aatyush"]], "s3:GetBucketNotification", f"arn:aws:s3:::taskcloud-attachments-{ACCOUNT}-{REGION}")
    assert allowed([USERS["aatyush"]], "apigateway:GET", f"arn:aws:apigateway:{REGION}::/apis/abc/routes")
    assert not any(a in actions_of(USERS["aatyush"]) for a in ("apigateway:POST", "apigateway:PATCH", "apigateway:DELETE"))


# --- Every call a script makes must be allowed for the person who runs it ---

CFN_DEPLOY_ACTIONS = ["CreateChangeSet", "DescribeChangeSet", "ExecuteChangeSet", "DescribeStacks", "DescribeStackEvents",
                      "GetTemplateSummary"]


def required_permissions(call):
    """Translate one recorded CLI call into the (action, resource) pairs it needs."""
    if call[0] == "curl":
        return []
    command = " ".join(call[:2])

    def flag(name):
        return call[call.index(name) + 1]

    if command == "sts get-caller-identity":
        return [("sts:GetCallerIdentity", "*")]
    if command == "cloudformation describe-stacks":
        return [("cloudformation:DescribeStacks", stack_arn(flag("--stack-name")))]
    if command == "cloudformation describe-stack-events":
        return [("cloudformation:DescribeStackEvents", stack_arn(flag("--stack-name")))]
    if command == "cloudformation list-exports":
        return [("cloudformation:ListExports", "*")]
    if command == "cloudformation deploy":
        arn = stack_arn(flag("--stack-name"))
        pairs = [(f"cloudformation:{a}", arn) for a in CFN_DEPLOY_ACTIONS]
        pairs.append(("iam:PassRole", f"arn:aws:iam::{ACCOUNT}:role/taskcloud-cfn-role"))
        return pairs
    if command == "cloudformation package":
        return [("s3:ListBucket", ARTIFACTS), ("s3:GetObject", f"{ARTIFACTS}/lambda/x"), ("s3:PutObject", f"{ARTIFACTS}/lambda/x")]
    if command == "dynamodb describe-table":
        return [("dynamodb:DescribeTable", f"arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/{flag('--table-name')}")]
    if command == "cognito-idp describe-user-pool":
        return [("cognito-idp:DescribeUserPool", f"arn:aws:cognito-idp:{REGION}:{ACCOUNT}:userpool/{flag('--user-pool-id')}")]
    if command.startswith("amplify "):
        action = {"create-deployment": "CreateDeployment", "start-deployment": "StartDeployment", "get-job": "GetJob"}[call[1]]
        return [(f"amplify:{action}", f"arn:aws:amplify:{REGION}:{ACCOUNT}:apps/{flag('--app-id')}/branches/main")]
    raise AssertionError(f"test_iam.py does not know what permission this call needs: {call[:2]}")


@needs_bash
@pytest.mark.parametrize("name, script", [("sanchit", "1_data.sh"), ("aatyush", "2_api.sh"), ("krushna", "4_frontend.sh")])
def test_script_calls_are_all_allowed_for_their_owner(sandbox, name, script):  # noqa: F811
    result = sandbox.run(script)
    assert result.returncode == 0, result.stdout
    assert sandbox.calls()
    for call in sandbox.calls():
        for action, resource in required_permissions(call):
            assert allowed([GROUP, USERS[name]], action, resource), f"{name} cannot {action} on {resource}: {call[:3]}"


# --- render_iam.sh ---


@needs_bash
def test_render_iam_fills_account_and_validates(sandbox):  # noqa: F811
    result = sandbox.run("render_iam.sh", "111122223333")
    assert result.returncode == 0, result.stdout
    rendered = list((sandbox.root / "iam" / "rendered").glob("*.json"))
    assert len(rendered) == 4
    for path in rendered:
        text = path.read_text()
        assert "<ACCOUNT_ID>" not in text and "111122223333" in text
        json.loads(text)
    # A fixed account argument never needs the CLI.
    assert sandbox.calls() == []


@needs_bash
def test_render_iam_rejects_bad_account(sandbox):  # noqa: F811
    assert sandbox.run("render_iam.sh", "12345").returncode != 0


def test_rendered_folder_is_git_ignored():
    subprocess.run(["git", "check-ignore", "-q", "iam/rendered/x.json"], cwd=REPO, check=True)
