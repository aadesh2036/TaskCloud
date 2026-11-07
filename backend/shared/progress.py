"""Progress counts and streaks, all computed in IST."""

from collections import Counter
from datetime import datetime, timedelta

from shared.timeutil import ist_date_of, today_ist


def compute_progress(tasks: list[dict], now: datetime) -> dict:
    today = today_ist(now)
    done_tasks = [t for t in tasks if t.get("status") == "done"]
    per_day = Counter(ist_date_of(t["completedAt"]) for t in done_tasks if t.get("completedAt"))

    # D-016: a streak is still alive if the last completion was yesterday, so it does
    # not read as zero every morning until the student finishes something.
    cursor = today if per_day[today] else today - timedelta(days=1)
    streak = 0
    while per_day[cursor]:
        streak += 1
        cursor -= timedelta(days=1)

    last_seven = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    return {
        "total": len(tasks),
        "done": len(done_tasks),
        "todo": len(tasks) - len(done_tasks),
        "completedToday": per_day[today],
        "streakDays": streak,
        "last7Days": [{"date": day.isoformat(), "done": per_day[day]} for day in last_seven],
    }
