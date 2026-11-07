"""Runs the real deploy scripts against a fake aws CLI, to test flow, order and failure handling.

The fake is first on PATH and credentials are dummies, so these tests cannot reach AWS.
They check what the scripts ask for, not whether AWS would accept it.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = sorted((REPO / "scripts").glob("*.sh")) + sorted((REPO / "scripts" / "lib").glob("*.sh"))
EXPECTED_SCRIPTS = {
    "build_lambdas.sh", "0_foundation.sh", "1_data.sh", "2_api.sh", "3_agent.sh", "4_frontend.sh",
    "create_demo_user.sh", "render_iam.sh", "99_teardown.sh", "common.sh",
}
FAILURE_LINE = "Do not fix this in the console. Send this log file to Aadesh."

needs_bash = pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="needs bash")

FAKE_AWS = r'''#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps(args) + "\n")
command = " ".join(args[:2])
query = args[args.index("--query") + 1] if "--query" in args else ""
def arg(name):
    return args[args.index(name) + 1] if name in args else ""
if command in os.environ.get("FAKE_FAIL", "").split(","):
    print("fake failure: " + command, file=sys.stderr)
    sys.exit(254)
OUTPUTS = {
    "UserPoolId": "ap-south-1_POOL", "UserPoolClientId": "clientid", "ApiEndpoint": "https://api.test.invalid",
    "ApiId": "apiid", "AmplifyAppId": "appid", "SiteUrl": "https://main.appid.amplifyapp.test",
}
if command == "sts get-caller-identity":
    print("111122223333" if "Account" in query else json.dumps({"Account": "111122223333", "Arn": "arn:aws:iam::111122223333:user/test"}))
elif command == "cloudformation describe-stacks":
    stack = arg("--stack-name")
    statuses = json.loads(os.environ.get("FAKE_STATUSES", "{}"))
    status = statuses.get(stack, "CREATE_COMPLETE")
    if status == "MISSING":
        print("Stack does not exist", file=sys.stderr); sys.exit(254)
    match = re.search(r"OutputKey=='(\w+)'", query)
    if "StackStatus" in query:
        print(status)
    elif match:
        print(OUTPUTS.get(match.group(1), "None"))
    else:
        print("outputs-table")
elif command == "cloudformation list-exports":
    if "CfnRoleArn" in query:
        print(os.environ.get("FAKE_ROLE", "arn:aws:iam::111122223333:role/taskcloud-cfn-role"))
    else:
        print("taskcloud-artifacts-111122223333-ap-south-1")
elif command == "cloudformation package":
    with open(arg("--output-template-file"), "w") as f:
        f.write("packaged\n")
elif command == "amplify create-deployment":
    print("7\thttps://upload.test.invalid/secret-upload-url")
elif command == "amplify get-job":
    print(os.environ.get("FAKE_JOB", "SUCCEED"))
elif command == "ssm get-parameter":
    if os.environ.get("FAKE_MODEL"):
        print(os.environ["FAKE_MODEL"])
    else:
        sys.exit(254)
elif command == "s3api head-bucket":
    pass
elif command == "cognito-idp admin-get-user":
    sys.exit(0 if os.environ.get("FAKE_USER_EXISTS") else 254)
'''

FAKE_CURL = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps(["curl"] + args) + "\n")
if "--write-out" in args:
    if "--output" in args:
        open(args[args.index("--output") + 1], "w").write('{"message":"Unauthorized"}')
    print(os.environ.get("FAKE_HTTP", "401"), end="")
'''

FAKE_NPM = r'''#!/usr/bin/env bash
echo "npm $*" >> "$FAKE_LOG.npm"
if [ "$1" = "run" ]; then mkdir -p dist/assets; echo "<html>" > dist/index.html; echo "x" > dist/assets/a.js; fi
'''

FAKE_SLEEP = "#!/usr/bin/env bash\nexit 0\n"


def _executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def sandbox(tmp_path):
    """A copy of the repo and a bin folder of fakes, so nothing in the real repo changes."""
    root = tmp_path / "repo"
    for folder in ("scripts", "infra", "iam"):
        shutil.copytree(REPO / folder, root / folder)
    (root / "backend").mkdir()
    shutil.copytree(REPO / "backend" / "shared", root / "backend" / "shared", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "backend" / "functions", root / "backend" / "functions", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "frontend").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "aws", FAKE_AWS)
    _executable(bin_dir / "curl", FAKE_CURL)
    _executable(bin_dir / "npm", FAKE_NPM)
    _executable(bin_dir / "sleep", FAKE_SLEEP)
    log = tmp_path / "calls.log"
    log.touch()
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(log),
        "AWS_ACCESS_KEY_ID": "dummy",
        "AWS_SECRET_ACCESS_KEY": "dummy",
        "AWS_CONFIG_FILE": os.devnull,
        "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
    }
    assert shutil.which("aws", path=env["PATH"]) == str(bin_dir / "aws")

    class Sandbox:
        def __init__(self):
            self.root, self.log = root, log

        def run(self, script, *args, input_text=None, **extra_env):
            return subprocess.run(
                ["bash", f"scripts/{script}", *args],
                cwd=root, env={**env, **extra_env}, input=input_text or "",
                capture_output=True, text=True, timeout=120,
            )

        def calls(self):
            return [json.loads(line) for line in log.read_text().splitlines()]

        def named(self, *prefix):
            return [c for c in self.calls() if c[: len(prefix)] == list(prefix)]

        def deploys(self):
            return self.named("cloudformation", "deploy")

    return Sandbox()


def value_after(call, flag):
    return call[call.index(flag) + 1]


# --- Static checks ---


def test_all_expected_scripts_exist():
    assert {p.name for p in SCRIPTS} == EXPECTED_SCRIPTS


@needs_bash
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script):
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.parametrize("script", [p for p in SCRIPTS if p.name != "common.sh"], ids=lambda p: p.name)
def test_scripts_use_strict_mode(script):
    assert "set -euo pipefail" in script.read_text(encoding="utf-8")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_scripts_have_lf_endings(script):
    assert b"\r" not in script.read_bytes()


def test_default_model_is_the_agreed_profile():
    assert "in.anthropic.claude-haiku-4-5-20251001-v1:0" in (REPO / "scripts/lib/common.sh").read_text(encoding="utf-8")


# --- Lambda build ---


@needs_bash
@pytest.mark.parametrize("function", ["tasks_api", "attachment_indexer", "planner_agent"])
def test_build_is_importable_without_third_party_packages(sandbox, function):
    result = sandbox.run("build_lambdas.sh")
    assert result.returncode == 0, result.stderr
    folder = sandbox.root / ".build" / function
    assert (folder / "handler.py").is_file() and (folder / "shared" / "store.py").is_file()
    assert not list(folder.rglob("__pycache__"))
    # -I ignores the environment, so this proves the folder alone is enough, as in Lambda,
    # which adds boto3 itself. boto3 is only imported when a client is first needed.
    check = subprocess.run(
        [sys.executable, "-I", "-S", "-c", "import sys; sys.path.insert(0, '.'); sys.dont_write_bytecode = True; "
         "import handler; print(callable(handler.lambda_handler))"],
        cwd=folder, capture_output=True, text=True,
    )
    assert check.stdout.strip() == "True", check.stderr


# --- Shared behaviour ---


@needs_bash
@pytest.mark.parametrize(
    "script, args",
    [("0_foundation.sh", ["me@example.com"]), ("1_data.sh", []), ("2_api.sh", []), ("3_agent.sh", [])],
)
def test_deploy_scripts_report_identity_and_stack_and_log(sandbox, script, args):
    result = sandbox.run(script, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Region: ap-south-1" in result.stdout
    assert sandbox.named("sts", "get-caller-identity")
    assert sandbox.named("cloudformation", "describe-stack-events")
    events = sandbox.named("cloudformation", "describe-stack-events")[0]
    assert value_after(events, "--max-items") == "20"
    logs = list((sandbox.root / "logs").glob(f"{script[:-3]}_*.log"))
    assert len(logs) == 1 and "Region: ap-south-1" in logs[0].read_text()
    deploy = sandbox.deploys()[0]
    assert "--no-fail-on-empty-changeset" in deploy
    assert value_after(deploy, "--capabilities") == "CAPABILITY_NAMED_IAM"


@needs_bash
def test_foundation_deploys_without_role_and_checks_model(sandbox):
    assert sandbox.run("0_foundation.sh", "me@example.com", "7").returncode == 0
    deploy = sandbox.deploys()[0]
    assert "--role-arn" not in deploy
    assert value_after(deploy, "--stack-name") == "taskcloud-foundation"
    assert "AlertEmail=me@example.com" in deploy and "BudgetLimit=7" in deploy
    assert sandbox.named("bedrock", "list-inference-profiles")
    converse = sandbox.named("bedrock-runtime", "converse")[0]
    assert value_after(converse, "--model-id") == "in.anthropic.claude-haiku-4-5-20251001-v1:0"


@needs_bash
def test_foundation_needs_an_email_and_deploys_nothing_without_one(sandbox):
    result = sandbox.run("0_foundation.sh")
    assert result.returncode != 0 and "email" in result.stdout
    assert sandbox.deploys() == []


@needs_bash
def test_foundation_model_check_failure_only_warns(sandbox):
    result = sandbox.run("0_foundation.sh", "me@example.com", FAKE_FAIL="bedrock-runtime converse")
    assert result.returncode == 0
    assert "WARNING" in result.stdout and "Nova" in result.stdout


@needs_bash
@pytest.mark.parametrize(
    "script, stack",
    [("1_data.sh", "taskcloud-data"), ("2_api.sh", "taskcloud-api"), ("3_agent.sh", "taskcloud-agent")],
)
def test_later_stacks_use_the_deploy_role(sandbox, script, stack):
    assert sandbox.run(script).returncode == 0
    deploy = sandbox.deploys()[0]
    assert value_after(deploy, "--stack-name") == stack
    assert value_after(deploy, "--role-arn") == "arn:aws:iam::111122223333:role/taskcloud-cfn-role"


@needs_bash
@pytest.mark.parametrize(
    "script, missing",
    [
        ("1_data.sh", "taskcloud-foundation"),
        ("2_api.sh", "taskcloud-data"),
        ("3_agent.sh", "taskcloud-api"),
        ("4_frontend.sh", "taskcloud-agent"),
    ],
)
@pytest.mark.parametrize("status", ["MISSING", "ROLLBACK_IN_PROGRESS", "UPDATE_ROLLBACK_COMPLETE"])
def test_prerequisite_not_ready_stops_before_deploy(sandbox, script, missing, status):
    result = sandbox.run(script, FAKE_STATUSES=json.dumps({missing: status}))
    assert result.returncode != 0
    assert f"Prerequisite stack {missing} is not ready" in result.stdout
    assert FAILURE_LINE in result.stdout
    assert sandbox.deploys() == []


@needs_bash
def test_update_complete_counts_as_ready(sandbox):
    assert sandbox.run("1_data.sh", FAKE_STATUSES='{"taskcloud-foundation": "UPDATE_COMPLETE"}').returncode == 0


@needs_bash
def test_failed_deploy_prints_message_events_and_exits_nonzero(sandbox):
    result = sandbox.run("1_data.sh", FAKE_FAIL="cloudformation deploy")
    assert result.returncode != 0
    assert FAILURE_LINE in result.stdout and "Log file:" in result.stdout
    assert sandbox.named("cloudformation", "describe-stack-events")
    log = next((sandbox.root / "logs").glob("1_data_*.log")).read_text()
    assert FAILURE_LINE in log


@needs_bash
def test_rolled_back_stack_gets_clear_message(sandbox):
    result = sandbox.run("1_data.sh", FAKE_STATUSES='{"taskcloud-data": "ROLLBACK_COMPLETE"}')
    assert result.returncode != 0 and "ROLLBACK_COMPLETE" in result.stdout
    assert sandbox.deploys() == []


@needs_bash
def test_missing_role_export_stops(sandbox):
    result = sandbox.run("1_data.sh", FAKE_ROLE="None")
    assert result.returncode != 0 and "0_foundation.sh" in result.stdout
    assert sandbox.deploys() == []


@needs_bash
def test_scripts_are_safe_to_rerun(sandbox):
    assert sandbox.run("2_api.sh").returncode == 0
    assert sandbox.run("2_api.sh").returncode == 0
    assert len(sandbox.deploys()) == 2


# --- Individual scripts ---


@needs_bash
def test_data_prints_evidence(sandbox):
    assert sandbox.run("1_data.sh").returncode == 0
    assert sandbox.named("dynamodb", "describe-table")
    assert value_after(sandbox.named("cognito-idp", "describe-user-pool")[0], "--user-pool-id") == "ap-south-1_POOL"


@needs_bash
def test_api_builds_packages_deploys_then_checks_401(sandbox):
    result = sandbox.run("2_api.sh")
    assert result.returncode == 0, result.stdout
    calls = sandbox.calls()
    package = next(i for i, c in enumerate(calls) if c[:2] == ["cloudformation", "package"])
    deploy = next(i for i, c in enumerate(calls) if c[:2] == ["cloudformation", "deploy"])
    curl = next(i for i, c in enumerate(calls) if c[0] == "curl")
    assert package < deploy < curl
    assert value_after(calls[package], "--s3-bucket") == "taskcloud-artifacts-111122223333-ap-south-1"
    assert value_after(calls[deploy], "--template-file") == "packaged-2_api.yaml"
    assert (sandbox.root / ".build" / "tasks_api" / "handler.py").is_file()
    assert "Authorization" not in " ".join(calls[curl])
    assert "returned HTTP 401" in result.stdout


@needs_bash
def test_api_fails_if_unauthenticated_call_is_not_401(sandbox):
    result = sandbox.run("2_api.sh", FAKE_HTTP="200")
    assert result.returncode != 0 and "Expected 401" in result.stdout


@needs_bash
def test_agent_applies_throttle_after_deploy(sandbox):
    result = sandbox.run("3_agent.sh")
    assert result.returncode == 0, result.stdout
    calls = sandbox.calls()
    deploy = next(i for i, c in enumerate(calls) if c[:2] == ["cloudformation", "deploy"])
    update = next(i for i, c in enumerate(calls) if c[:2] == ["apigatewayv2", "update-stage"])
    assert deploy < update
    assert value_after(calls[update], "--stage-name") == "$default"
    assert json.loads(value_after(calls[update], "--route-settings")) == {
        "POST /plan": {"ThrottlingBurstLimit": 2, "ThrottlingRateLimit": 2}
    }
    assert "curl -i -X POST" in result.stdout and "https://api.test.invalid/plan" in result.stdout
    assert "ModelId=in.anthropic.claude-haiku-4-5-20251001-v1:0" in calls[deploy]


@needs_bash
def test_agent_rerun_keeps_a_switched_model(sandbox):
    assert sandbox.run("3_agent.sh", FAKE_MODEL="apac.amazon.nova-lite-v1:0").returncode == 0
    assert "ModelId=apac.amazon.nova-lite-v1:0" in sandbox.deploys()[0]


@needs_bash
def test_frontend_full_flow(sandbox):
    result = sandbox.run("4_frontend.sh")
    assert result.returncode == 0, result.stdout
    assert "node v" in result.stdout
    assert value_after(sandbox.deploys()[0], "--template-file") == "infra/4_frontend.yaml"

    config = json.loads((sandbox.root / "frontend" / "dist" / "config.json").read_text())
    assert config == {
        "mode": "aws",
        "region": "ap-south-1",
        "apiUrl": "https://api.test.invalid",
        "userPoolId": "ap-south-1_POOL",
        "userPoolClientId": "clientid",
    }
    with zipfile.ZipFile(sandbox.root / ".build" / "frontend.zip") as archive:
        names = archive.namelist()
    # The contents of dist/, not the folder itself.
    assert "index.html" in names and "config.json" in names and "assets/a.js" in names
    assert not any(name.startswith("dist") for name in names)

    calls = sandbox.calls()
    create = next(i for i, c in enumerate(calls) if c[:2] == ["amplify", "create-deployment"])
    put = next(i for i, c in enumerate(calls) if c[0] == "curl" and "PUT" in c)
    start = next(i for i, c in enumerate(calls) if c[:2] == ["amplify", "start-deployment"])
    poll = next(i for i, c in enumerate(calls) if c[:2] == ["amplify", "get-job"])
    assert create < put < start < poll
    assert "https://upload.test.invalid/secret-upload-url" in calls[put]
    assert value_after(calls[start], "--job-id") == "7"
    assert "Site URL: https://main.appid.amplifyapp.test" in result.stdout
    # The upload URL works without any other credentials, so it must stay out of the log.
    assert "secret-upload-url" not in result.stdout


@needs_bash
def test_frontend_reports_failed_amplify_job(sandbox):
    result = sandbox.run("4_frontend.sh", FAKE_JOB="FAILED")
    assert result.returncode != 0 and "status FAILED" in result.stdout and FAILURE_LINE in result.stdout


@needs_bash
def test_frontend_times_out_on_stuck_job(sandbox):
    result = sandbox.run("4_frontend.sh", FAKE_JOB="RUNNING")
    assert result.returncode != 0 and "did not finish" in result.stdout
    assert len(sandbox.named("amplify", "get-job")) == 60


@needs_bash
def test_frontend_refuses_old_node(sandbox, tmp_path):
    (tmp_path / "bin" / "node").write_text('#!/usr/bin/env bash\nif [ "$1" = "-v" ]; then echo v16.20.0; else echo 16; fi\n')
    (tmp_path / "bin" / "node").chmod(0o755)
    result = sandbox.run("4_frontend.sh")
    assert result.returncode != 0 and "Node 18 or later" in result.stdout
    assert sandbox.deploys() == []


@needs_bash
def test_demo_user_is_suppressed_permanent_and_password_stays_out_of_log(sandbox):
    result = sandbox.run("create_demo_user.sh", "demo@example.com", input_text="S3cretPass1\n")
    assert result.returncode == 0, result.stdout
    create = sandbox.named("cognito-idp", "admin-create-user")[0]
    assert value_after(create, "--message-action") == "SUPPRESS"
    password = sandbox.named("cognito-idp", "admin-set-user-password")[0]
    assert "--permanent" in password and value_after(password, "--password") == "S3cretPass1"
    assert "S3cretPass1" not in result.stdout
    assert "S3cretPass1" not in next((sandbox.root / "logs").glob("create_demo_user_*.log")).read_text()


@needs_bash
def test_demo_user_rerun_only_changes_password(sandbox):
    assert sandbox.run("create_demo_user.sh", "demo@example.com", input_text="S3cretPass1\n", FAKE_USER_EXISTS="1").returncode == 0
    assert sandbox.named("cognito-idp", "admin-create-user") == []
    assert sandbox.named("cognito-idp", "admin-set-user-password")


@needs_bash
def test_teardown_needs_exact_confirmation(sandbox):
    for answer in ("", "yes\n", "delete\n"):
        result = sandbox.run("99_teardown.sh", input_text=answer)
        assert "Nothing was deleted" in result.stdout or result.returncode != 0
    assert sandbox.named("cloudformation", "delete-stack") == []
    assert sandbox.named("s3", "rm") == []


@needs_bash
def test_teardown_order_and_empties_buckets_first(sandbox):
    result = sandbox.run("99_teardown.sh", input_text="DELETE\n")
    assert result.returncode == 0, result.stdout
    calls = sandbox.calls()
    deletes = [value_after(c, "--stack-name") for c in calls if c[:2] == ["cloudformation", "delete-stack"]]
    assert deletes == ["taskcloud-frontend", "taskcloud-agent", "taskcloud-api", "taskcloud-data", "taskcloud-foundation"]
    waits = [value_after(c, "--stack-name") for c in calls if c[:3] == ["cloudformation", "wait", "stack-delete-complete"]]
    assert waits == deletes

    index = {
        c[2]: i for i, c in enumerate(calls) if c[:2] == ["s3", "rm"]
    }
    api_delete = calls.index(["cloudformation", "delete-stack", "--stack-name", "taskcloud-api"])
    foundation_delete = calls.index(["cloudformation", "delete-stack", "--stack-name", "taskcloud-foundation"])
    assert index["s3://taskcloud-attachments-111122223333-ap-south-1"] < api_delete
    assert index["s3://taskcloud-artifacts-111122223333-ap-south-1"] < foundation_delete
    assert index["s3://taskcloud-trail-111122223333-ap-south-1"] < foundation_delete
    stop = next(i for i, c in enumerate(calls) if c[:2] == ["cloudtrail", "stop-logging"])
    assert stop < index["s3://taskcloud-trail-111122223333-ap-south-1"]


@needs_bash
def test_teardown_skips_missing_stacks(sandbox):
    statuses = {"taskcloud-frontend": "MISSING", "taskcloud-agent": "MISSING"}
    result = sandbox.run("99_teardown.sh", input_text="DELETE\n", FAKE_STATUSES=json.dumps(statuses))
    assert result.returncode == 0
    deletes = [value_after(c, "--stack-name") for c in sandbox.named("cloudformation", "delete-stack")]
    assert deletes == ["taskcloud-api", "taskcloud-data", "taskcloud-foundation"]
