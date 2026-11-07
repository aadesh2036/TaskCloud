from datetime import date

import pytest
from shared.responses import ApiError
from shared.validation import (
    clean_new_task,
    clean_patch,
    clean_planned_task,
    parse_attachment_key,
    require_task_id,
    sanitize_filename,
)

GOOD_ID = "3f2b1c9e-8a47-4d21-9b6f-0c1d2e3f4a5b"
TODAY = date(2026, 11, 7)


def planned(**overrides):
    return {"title": "Revise", "dueDate": "2026-11-10", "priority": "high", "estMinutes": 60, **overrides}


@pytest.mark.parametrize(
    "body",
    [
        {"dueDate": "2026-11-10"},
        {"title": "x"},
        {"title": "", "dueDate": "2026-11-10"},
        {"title": "   ", "dueDate": "2026-11-10"},
        {"title": "x" * 121, "dueDate": "2026-11-10"},
        {"title": 5, "dueDate": "2026-11-10"},
        {"title": "x", "dueDate": "2026-13-01"},
        {"title": "x", "dueDate": "2026-02-30"},
        {"title": "x", "dueDate": "20261110"},
        {"title": "x", "dueDate": "2026-11-10T00:00:00"},
        {"title": "x", "dueDate": "2026-11-10", "priority": "urgent"},
        {"title": "x", "dueDate": "2026-11-10", "estMinutes": 4},
        {"title": "x", "dueDate": "2026-11-10", "estMinutes": 481},
        {"title": "x", "dueDate": "2026-11-10", "estMinutes": 30.5},
        {"title": "x", "dueDate": "2026-11-10", "estMinutes": True},
        {"title": "x", "dueDate": "2026-11-10", "estMinutes": "30"},
        {"title": "x", "dueDate": "2026-11-10", "userId": "someone-else"},
        {"title": "x", "dueDate": "2026-11-10", "source": "agent"},
        {"title": "x", "dueDate": "2026-11-10", "attachmentKey": "a/b/c"},
    ],
)
def test_new_task_rejected(body):
    with pytest.raises(ApiError) as exc:
        clean_new_task(body)
    assert exc.value.status == 400


def test_new_task_boundaries_and_defaults():
    assert clean_new_task({"title": " x" + "y" * 119, "dueDate": "2026-11-10"}) == {
        "title": "x" + "y" * 119,
        "dueDate": "2026-11-10",
        "priority": "medium",
        "estMinutes": 30,
    }
    assert clean_new_task({"title": "x", "dueDate": "2026-11-10", "estMinutes": 5})["estMinutes"] == 5
    assert clean_new_task({"title": "x", "dueDate": "2026-11-10", "estMinutes": 480})["estMinutes"] == 480


def test_patch_allows_only_listed_fields():
    assert clean_patch({"status": "done"}) == {"status": "done"}
    for body in ({}, {"userId": "x"}, {"source": "agent"}, {"completedAt": "now"}, {"status": "doing"}):
        with pytest.raises(ApiError):
            clean_patch(body)


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"dueDate": "2026-11-06"}, "past"),
        ({"dueDate": "2027-01-07"}, "60 days"),
        ({"dueDate": "soon"}, "YYYY-MM-DD"),
        ({"title": ""}, "title"),
        ({"title": "x" * 121}, "120"),
        ({"priority": "critical"}, "priority"),
        ({"estMinutes": 1000}, "estMinutes"),
        ({"estMinutes": None}, "estMinutes"),
    ],
)
def test_planned_task_rejected_with_reason(overrides, reason):
    with pytest.raises(ValueError, match=reason):
        clean_planned_task(planned(**overrides), TODAY)


def test_planned_task_date_boundaries():
    assert clean_planned_task(planned(dueDate="2026-11-07"), TODAY)["dueDate"] == "2026-11-07"
    assert clean_planned_task(planned(dueDate="2027-01-06"), TODAY)["dueDate"] == "2027-01-06"


def test_planned_task_drops_extra_fields():
    clean = clean_planned_task(planned(userId="victim", source="manual", status="done"), TODAY)
    assert set(clean) == {"title", "dueDate", "priority", "estMinutes"}


def test_task_id_format():
    assert require_task_id(GOOD_ID) == GOOD_ID
    for bad in ("1", "../etc", GOOD_ID.upper(), GOOD_ID + "0", None, "3f2b1c9e-8a47-1d21-9b6f-0c1d2e3f4a5b"):
        with pytest.raises(ApiError):
            require_task_id(bad)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("notes.pdf", "notes.pdf"),
        ("my notes (final).pdf", "my_notes_final_.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\report.docx", "report.docx"),
        (".hidden", "hidden"),
        ("परीक्षा.pdf", "_.pdf"),
        ("...", "file"),
    ],
)
def test_sanitize_filename(name, expected):
    assert sanitize_filename(name) == expected


def test_sanitize_filename_keeps_extension_when_long():
    result = sanitize_filename("a" * 300 + ".pdf")
    assert len(result) == 100 and result.endswith(".pdf")


def test_sanitize_filename_requires_a_name():
    for bad in (None, "", "   ", 7):
        with pytest.raises(ApiError):
            sanitize_filename(bad)


def test_parse_attachment_key():
    assert parse_attachment_key(f"user-1/{GOOD_ID}/a.pdf") == ("user-1", GOOD_ID)
    for bad in ("", "a", "a/b", f"user-1/{GOOD_ID}", f"user-1/{GOOD_ID}/", f"user/1/{GOOD_ID}/a.pdf",
                "user-1/not-a-uuid/a.pdf", f"user-1/{GOOD_ID}/..", f"us er/{GOOD_ID}/a.pdf", f"/{GOOD_ID}/a.pdf"):
        assert parse_attachment_key(bad) is None
