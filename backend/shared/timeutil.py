"""Time helpers. All student-facing dates are in IST (UTC+05:30)."""

from datetime import UTC, date, datetime, timedelta, timezone

# A fixed offset rather than zoneinfo: India has no daylight saving, and the Lambda
# zip stays free of any dependency on the tzdata package.
IST = timezone(timedelta(hours=5, minutes=30), "IST")


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_ist(moment: datetime | None = None) -> date:
    return (moment or now_utc()).astimezone(IST).date()


def ist_date_of(iso_timestamp: str) -> date:
    return datetime.fromisoformat(iso_timestamp).astimezone(IST).date()
