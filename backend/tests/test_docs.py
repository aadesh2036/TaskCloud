"""Every file and script named in the docs must exist under exactly that name."""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = [REPO / "README.md", REPO / "CLAUDE.md", *sorted((REPO / "docs").glob("*.md"))]
CODE_SPAN = re.compile(r"`([^`\n]+)`")
PATH_PREFIXES = ("backend/", "docs/", "frontend/", "iam/", "infra/", "local/", "scripts/")
# Generated at run time and git-ignored, so they are not expected in a clean checkout.
GENERATED = ("iam/rendered", "frontend/public/config.json", "frontend/dist/", "local/.data")


def named_paths(doc: Path):
    for span in CODE_SPAN.findall(doc.read_text(encoding="utf-8")):
        for word in span.split():
            word = word.strip("'\",;:()").rstrip(".")
            if not word.startswith(PATH_PREFIXES) or word.startswith(GENERATED):
                continue
            if "<" in word or "/local/" in word:
                continue
            yield word


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_named_paths_exist(doc):
    missing = []
    for path in named_paths(doc):
        if "*" in path:
            found = list(REPO.glob(path))
        else:
            found = (REPO / path).exists()
        if not found:
            missing.append(path)
    assert not missing, f"{doc.name} names files that do not exist: {sorted(set(missing))}"


@pytest.mark.parametrize(
    "name",
    ["CLAUDE.md", "AGENTS.md", "README.md", "requirements-dev.txt", "docs/ARCHITECTURE.md", "docs/TILLNOW.md",
     "docs/DECISIONS.md", "docs/DEPLOYMENT.md", "docs/IAM_ACL.md", "docs/LOCAL_DEV.md", "logs/.gitkeep",
     "frontend/package-lock.json", "local/server.py", "local/smoke_test.py"],
)
def test_required_files_exist(name):
    assert (REPO / name).is_file()


def test_tillnow_has_the_required_sections_in_order():
    text = (REPO / "docs" / "TILLNOW.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (.+)$", text, re.M)
    assert sections == ["Last updated", "Current state", "Milestones", "Next step", "Open questions and blockers", "Change log"]
    for milestone in range(10):
        assert f"| M{milestone} |" in text


def test_every_decision_has_the_required_fields_and_is_numbered_in_order():
    text = (REPO / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    ids = [int(n) for n in re.findall(r"^## D-(\d{3}):", text, re.M)]
    assert ids == list(range(1, len(ids) + 1)) and len(ids) >= 13
    for entry in re.split(r"^## D-", text, flags=re.M)[1:]:
        for field in ("**Date:**", "**Decision:**", "**Reason:**", "**Alternatives:**", "**Files:**"):
            assert field in entry, entry[:40]


def test_no_secrets_or_account_ids_are_tracked():
    import subprocess

    files = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    account_id = re.compile(r"(?<![-\d])\d{12}(?![-\d])")  # not the tail of a UUID
    access_key = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")
    email = re.compile(r"[\w.+-]+@(gmail|yahoo|outlook|hotmail|vit)\.[\w.]+")
    allowed_numbers = {"package-lock.json"}
    skipped_suffixes = (".pdf",)
    problems = []
    for name in filter(None, files):
        path = REPO / name
        if name.endswith(skipped_suffixes) or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if access_key.search(text) or email.search(text):
            problems.append(name)
        if path.name not in allowed_numbers and not name.startswith("backend/tests/") and account_id.search(text):
            problems.append(name)
    assert not problems, problems
