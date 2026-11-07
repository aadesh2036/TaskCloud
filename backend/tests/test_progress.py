from datetime import UTC, datetime

from shared.progress import compute_progress

# 2026-11-07 10:00 IST
NOW = datetime(2026, 11, 7, 4, 30, tzinfo=UTC)


def done_at(iso):
    return {"status": "done", "completedAt": iso}


def test_empty():
    result = compute_progress([], NOW)
    assert result["total"] == result["done"] == result["todo"] == 0
    assert result["streakDays"] == 0 and result["completedToday"] == 0
    assert [d["date"] for d in result["last7Days"]] == [
        "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07",
    ]


def test_counts():
    tasks = [{"status": "todo"}, done_at("2026-11-07T01:00:00Z"), done_at("2026-11-07T02:00:00Z")]
    result = compute_progress(tasks, NOW)
    assert (result["total"], result["done"], result["todo"], result["completedToday"]) == (3, 2, 1, 2)
    assert result["last7Days"][-1] == {"date": "2026-11-07", "done": 2}


def test_utc_evening_counts_as_next_ist_day():
    # 19:00 UTC on the 6th is 00:30 IST on the 7th.
    assert compute_progress([done_at("2026-11-06T19:00:00Z")], NOW)["completedToday"] == 1
    # 18:29 UTC on the 6th is 23:59 IST on the 6th.
    result = compute_progress([done_at("2026-11-06T18:29:00Z")], NOW)
    assert result["completedToday"] == 0
    assert result["last7Days"][-2] == {"date": "2026-11-06", "done": 1}


def test_streak_includes_today():
    tasks = [done_at("2026-11-07T01:00:00Z"), done_at("2026-11-06T01:00:00Z"), done_at("2026-11-05T01:00:00Z")]
    assert compute_progress(tasks, NOW)["streakDays"] == 3


def test_streak_survives_until_day_ends():
    tasks = [done_at("2026-11-06T01:00:00Z"), done_at("2026-11-05T01:00:00Z")]
    assert compute_progress(tasks, NOW)["streakDays"] == 2


def test_streak_breaks_on_gap():
    tasks = [done_at("2026-11-07T01:00:00Z"), done_at("2026-11-05T01:00:00Z")]
    assert compute_progress(tasks, NOW)["streakDays"] == 1
    assert compute_progress([done_at("2026-11-05T01:00:00Z")], NOW)["streakDays"] == 0


def test_todo_with_stale_completed_at_is_ignored():
    assert compute_progress([{"status": "todo", "completedAt": "2026-11-07T01:00:00Z"}], NOW)["streakDays"] == 0
