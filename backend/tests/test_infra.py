"""Checks the templates against the agreed design. cfn-lint checks they are valid CloudFormation.

These tests check they are the right CloudFormation: names, routes, exports and permissions.
"""

import re
from pathlib import Path

import pytest
import yaml
from functions.planner_agent.handler import MAX_TASKS_PER_PLAN
from functions.tasks_api.handler import ROUTES

REPO = Path(__file__).resolve().parents[2]
STACKS = ["0_foundation", "1_data", "2_api", "3_agent", "4_frontend"]
STACK_NAMES = {
    "0_foundation": "taskcloud-foundation",
    "1_data": "taskcloud-data",
    "2_api": "taskcloud-api",
    "3_agent": "taskcloud-agent",
    "4_frontend": "taskcloud-frontend",
}


class _Loader(yaml.SafeLoader):
    pass


def _tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    return {f"!{suffix}": value}


_Loader.add_multi_constructor("!", _tag)


def load(stack):
    return yaml.load((REPO / "infra" / f"{stack}.yaml").read_text(encoding="utf-8"), Loader=_Loader)


TEMPLATES = {stack: load(stack) for stack in STACKS}


def resources(stack, resource_type=None):
    items = TEMPLATES[stack]["Resources"].items()
    return {k: v for k, v in items if resource_type is None or v["Type"] == resource_type}


def all_resources(resource_type):
    found = {}
    for stack in STACKS:
        found.update(resources(stack, resource_type))
    return found


def flatten(value):
    """Yield every string in a nested structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item)


def policy_actions(role, sid=None):
    actions = set()
    for policy in role["Properties"]["Policies"]:
        for statement in policy["PolicyDocument"]["Statement"]:
            if statement["Effect"] == "Allow" and (sid is None or statement.get("Sid") == sid):
                action = statement["Action"]
                actions.update([action] if isinstance(action, str) else action)
    return actions


def text_of(value):
    return " ".join(flatten(value))


# --- Names and structure ---


def test_only_allowed_services_are_used():
    banned = re.compile(r"AWS::(EC2|ElasticLoadBalancing|RDS|SNS|SQS|ECS|EKS|ElastiCache|Serverless)")
    for stack in STACKS:
        for name, resource in resources(stack).items():
            assert not banned.search(resource["Type"]), f"{stack} {name}"
        assert "Transform" not in TEMPLATES[stack]


NAME_PROPERTIES = {
    "AWS::IAM::Role": "RoleName",
    "AWS::Lambda::Function": "FunctionName",
    "AWS::DynamoDB::Table": "TableName",
    "AWS::S3::Bucket": "BucketName",
    "AWS::Cognito::UserPool": "UserPoolName",
    "AWS::Cognito::UserPoolClient": "ClientName",
    "AWS::ApiGatewayV2::Api": "Name",
    "AWS::ApiGatewayV2::Authorizer": "Name",
    "AWS::CloudTrail::Trail": "TrailName",
    "AWS::Amplify::App": "Name",
}


@pytest.mark.parametrize("resource_type, prop", NAME_PROPERTIES.items())
def test_named_resources_use_the_prefix(resource_type, prop):
    found = all_resources(resource_type)
    assert found, resource_type
    for name, resource in found.items():
        assert text_of(resource["Properties"][prop]).split(" ")[-1].startswith("taskcloud-"), name


def test_budget_log_groups_and_parameter_use_the_prefix():
    assert resources("0_foundation", "AWS::Budgets::Budget")["Budget"]["Properties"]["Budget"]["BudgetName"].startswith("taskcloud-")
    for name, group in all_resources("AWS::Logs::LogGroup").items():
        assert group["Properties"]["LogGroupName"].startswith("/aws/lambda/taskcloud-"), name
        assert group["Properties"]["RetentionInDays"] == 7, name
    assert resources("3_agent", "AWS::SSM::Parameter")["ModelIdParameter"]["Properties"]["Name"] == "/taskcloud/modelId"


def test_data_resources_delete_with_their_stack():
    for resource_type in ("AWS::S3::Bucket", "AWS::DynamoDB::Table", "AWS::Cognito::UserPool", "AWS::Logs::LogGroup"):
        for name, resource in all_resources(resource_type).items():
            assert resource["DeletionPolicy"] == "Delete", name


def test_buckets_block_public_access_and_disable_acls():
    buckets = all_resources("AWS::S3::Bucket")
    assert len(buckets) == 3
    for name, bucket in buckets.items():
        props = bucket["Properties"]
        assert set(props["PublicAccessBlockConfiguration"].values()) == {True}, name
        assert props["OwnershipControls"]["Rules"][0]["ObjectOwnership"] == "BucketOwnerEnforced", name
        rule = props["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]
        assert rule["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256", name


# --- Exports and imports ---


def exports_of(stack):
    return {output["Export"]["Name"] for output in TEMPLATES[stack].get("Outputs", {}).values()}


def imports_of(stack):
    found = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "!ImportValue":
                    found.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(TEMPLATES[stack])
    return found


def test_exports_are_named_stack_dash_output():
    for stack in STACKS:
        for key, output in TEMPLATES[stack]["Outputs"].items():
            assert output["Export"]["Name"] == f"{STACK_NAMES[stack]}-{key}"


@pytest.mark.parametrize(
    "stack, expected",
    [
        ("0_foundation", {"CfnRoleArn", "ArtifactBucket"}),
        ("1_data", {"TableName", "TableArn", "UserPoolId", "UserPoolArn", "UserPoolClientId"}),
        ("2_api", {"ApiId", "ApiEndpoint", "AuthorizerId", "AttachmentsBucket"}),
        ("3_agent", {"PlannerFunctionArn"}),
        ("4_frontend", {"AmplifyAppId", "AmplifyDefaultDomain", "SiteUrl"}),
    ],
)
def test_stack_exports_match_design(stack, expected):
    assert set(TEMPLATES[stack]["Outputs"]) == expected


def test_imports_only_come_from_earlier_stacks():
    available = set()
    for stack in STACKS:
        assert imports_of(stack) <= available, stack
        available |= exports_of(stack)


# --- API ---


def test_every_route_needs_a_jwt_and_matches_a_handler():
    routes = {**resources("2_api", "AWS::ApiGatewayV2::Route"), **resources("3_agent", "AWS::ApiGatewayV2::Route")}
    keys = {route["Properties"]["RouteKey"] for route in routes.values()}
    assert keys == set(ROUTES) | {"POST /plan"}
    assert not any(key.startswith("OPTIONS") for key in keys)
    for name, route in routes.items():
        assert route["Properties"]["AuthorizationType"] == "JWT", name
        assert route["Properties"]["AuthorizerId"], name


def test_api_settings():
    api = resources("2_api", "AWS::ApiGatewayV2::Api")["HttpApi"]["Properties"]
    assert api["ProtocolType"] == "HTTP"
    assert api["CorsConfiguration"]["AllowOrigins"] == ["*"]
    assert set(api["CorsConfiguration"]["AllowHeaders"]) == {"authorization", "content-type"}
    assert set(api["CorsConfiguration"]["AllowMethods"]) == {"GET", "POST", "PATCH", "DELETE", "OPTIONS"}

    stage = resources("2_api", "AWS::ApiGatewayV2::Stage")["DefaultStage"]["Properties"]
    assert stage["StageName"] == "$default" and stage["AutoDeploy"] is True
    assert stage["DefaultRouteSettings"] == {"ThrottlingBurstLimit": 10, "ThrottlingRateLimit": 5}
    assert "RouteSettings" not in stage  # D-009

    integrations = {
        **resources("2_api", "AWS::ApiGatewayV2::Integration"),
        **resources("3_agent", "AWS::ApiGatewayV2::Integration"),
    }
    assert len(integrations) == 2
    for integration in integrations.values():
        assert integration["Properties"]["PayloadFormatVersion"] == "2.0"
        assert integration["Properties"]["TimeoutInMillis"] == 29000


def test_authorizer_uses_cognito_issuer_and_client_audience():
    props = resources("2_api", "AWS::ApiGatewayV2::Authorizer")["JwtAuthorizer"]["Properties"]
    assert props["AuthorizerType"] == "JWT"
    assert "https://cognito-idp.${AWS::Region}.amazonaws.com/${PoolId}" in text_of(props["JwtConfiguration"]["Issuer"])
    assert "taskcloud-data-UserPoolClientId" in text_of(props["JwtConfiguration"]["Audience"])


def test_cognito_signup_is_off_and_client_has_no_secret():
    pool = resources("1_data", "AWS::Cognito::UserPool")["UserPool"]["Properties"]
    assert pool["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
    assert pool["UsernameAttributes"] == ["email"]
    client = resources("1_data", "AWS::Cognito::UserPoolClient")["UserPoolClient"]["Properties"]
    assert client["GenerateSecret"] is False
    assert set(client["ExplicitAuthFlows"]) == {"ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"}


def test_table_keys():
    table = resources("1_data", "AWS::DynamoDB::Table")["TasksTable"]["Properties"]
    assert table["TableName"] == "taskcloud-tasks" and table["BillingMode"] == "PAY_PER_REQUEST"
    assert table["KeySchema"] == [
        {"AttributeName": "userId", "KeyType": "HASH"},
        {"AttributeName": "taskId", "KeyType": "RANGE"},
    ]


# --- Lambda ---


FUNCTIONS = {
    "taskcloud-tasks-api": "tasks_api",
    "taskcloud-attachment-indexer": "attachment_indexer",
    "taskcloud-planner-agent": "planner_agent",
}


def test_lambda_settings_and_code_paths():
    functions = all_resources("AWS::Lambda::Function")
    assert {f["Properties"]["FunctionName"] for f in functions.values()} == set(FUNCTIONS)
    for function in functions.values():
        props = function["Properties"]
        folder = FUNCTIONS[props["FunctionName"]]
        assert props["Runtime"] == "python3.13"
        assert props["Handler"] == "handler.lambda_handler"
        assert props["Code"] == f"../.build/{folder}"
        assert (REPO / "backend" / "functions" / folder / "handler.py").is_file()
        assert function["DependsOn"].endswith("LogGroup"), "log group must exist first"


def test_planner_timeout_and_memory():
    props = resources("3_agent", "AWS::Lambda::Function")["PlannerFunction"]["Properties"]
    assert props["Timeout"] == 28 and props["MemorySize"] == 512
    assert MAX_TASKS_PER_PLAN == 20


def test_default_model_is_the_agreed_profile():
    default = TEMPLATES["3_agent"]["Parameters"]["ModelId"]["Default"]
    assert default == "apac.amazon.nova-lite-v1:0"


def test_s3_to_lambda_cycle_is_avoided():
    bucket = resources("2_api", "AWS::S3::Bucket")["AttachmentsBucket"]
    assert bucket["DependsOn"] == "IndexerS3Permission"
    permission = resources("2_api", "AWS::Lambda::Permission")["IndexerS3Permission"]["Properties"]
    assert permission["SourceArn"] == {"!Sub": "arn:aws:s3:::taskcloud-attachments-${AWS::AccountId}-${AWS::Region}"}
    config = bucket["Properties"]["NotificationConfiguration"]["LambdaConfigurations"][0]
    assert config["Event"] == "s3:ObjectCreated:*"
    methods = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]["AllowedMethods"]
    assert set(methods) == {"POST", "GET"}


def test_amplify_app_has_no_repo_and_keeps_config_json():
    app = resources("4_frontend", "AWS::Amplify::App")["AmplifyApp"]["Properties"]
    assert app["Platform"] == "WEB" and "Repository" not in app
    rule = app["CustomRules"][0]
    assert rule["Target"] == "/index.html" and rule["Status"] == "200"
    # The rewrite must not swallow config.json, or the app would load index.html as its config.
    assert "json" in rule["Source"]
    branch = resources("4_frontend", "AWS::Amplify::Branch")["MainBranch"]["Properties"]
    assert branch["BranchName"] == "main" and branch["EnableAutoBuild"] is False


# --- IAM service roles match docs/IAM_ACL.md ---


LOG_ACTIONS = {"logs:CreateLogStream", "logs:PutLogEvents"}


def test_tasks_api_role_is_exact():
    role = resources("2_api", "AWS::IAM::Role")["TasksApiRole"]
    assert role["Properties"]["RoleName"] == "taskcloud-tasks-api-role"
    assert policy_actions(role) == LOG_ACTIONS | {
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query",
        "s3:PutObject", "s3:GetObject", "s3:DeleteObject",
    }


def test_indexer_role_is_exact():
    role = resources("2_api", "AWS::IAM::Role")["IndexerRole"]
    assert role["Properties"]["RoleName"] == "taskcloud-indexer-role"
    assert policy_actions(role) == LOG_ACTIONS | {"dynamodb:UpdateItem"}


def test_planner_role_is_exact():
    role = resources("3_agent", "AWS::IAM::Role")["PlannerRole"]
    assert role["Properties"]["RoleName"] == "taskcloud-planner-role"
    assert policy_actions(role) == LOG_ACTIONS | {
        "bedrock:InvokeModel", "ssm:GetParameter", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:BatchWriteItem",
    }
    resources_text = text_of(role["Properties"]["Policies"])
    assert "arn:aws:bedrock:*:${AWS::AccountId}:inference-profile/*" in resources_text
    assert "arn:aws:bedrock:*::foundation-model/*" in resources_text
    assert "parameter/taskcloud/modelId" in resources_text


def test_no_role_gets_wildcard_actions_or_managed_policies():
    for name, role in all_resources("AWS::IAM::Role").items():
        assert "ManagedPolicyArns" not in role["Properties"], name
        assert not any(action in ("*", "s3:*", "dynamodb:*") for action in policy_actions(role)), name


def test_deploy_role_trust_and_self_protection():
    role = resources("0_foundation", "AWS::IAM::Role")["CfnRole"]["Properties"]
    assert role["RoleName"] == "taskcloud-cfn-role"
    statement = role["AssumeRolePolicyDocument"]["Statement"][0]
    assert statement["Principal"] == {"Service": "cloudformation.amazonaws.com"}
    statements = [s for p in role["Policies"] for s in p["PolicyDocument"]["Statement"]]
    deny = next(s for s in statements if s["Effect"] == "Deny")
    assert deny["Action"] == "iam:*" and "role/taskcloud-cfn-role" in text_of(deny["Resource"])
    passing = next(s for s in statements if s.get("Sid") == "PassServiceRolesToLambdaOnly")
    assert passing["Condition"]["StringEquals"]["iam:PassedToService"] == "lambda.amazonaws.com"


def test_budget_alert_is_at_80_percent():
    budget = resources("0_foundation", "AWS::Budgets::Budget")["Budget"]["Properties"]
    notification = budget["NotificationsWithSubscribers"][0]["Notification"]
    assert notification["Threshold"] == 80 and notification["ThresholdType"] == "PERCENTAGE"
    assert TEMPLATES["0_foundation"]["Parameters"]["BudgetLimit"]["Default"] == 5
