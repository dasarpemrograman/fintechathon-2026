"""Date-only projections preserve local date semantics without invented instants."""

from copy import deepcopy
from datetime import date, timedelta
from packages.domain.economics import resolve_schedule, validate_date_graph
from services.api.store import DomainError


def project(identifier, milestones, calendars, trail=()):
    if not trail:
        validate_date_graph(milestones)
    if identifier in trail:
        raise DomainError("DATE_CYCLE", "Milestone graph contains a cycle.")
    milestone = milestones.get(identifier)
    if milestone is None:
        raise DomainError("ANCHOR_MISSING", "Milestone anchor is missing.")
    for kind in ["actual", "forecast", "agreed", "proposed"]:
        if milestone.get(kind):
            return deepcopy(milestone[kind])
    schedule = milestone["schedule"]
    if schedule["kind"] == "fixed":
        return deepcopy(schedule["due"])
    anchor = project(
        schedule["anchor_milestone_id"], milestones, calendars, trail + (identifier,)
    )
    if "instant" in anchor:
        resolved = resolve_schedule(schedule, milestones, calendars)
        timezone = (
            calendars[schedule["business_calendar_id"]]["timezone"]
            if schedule["day_basis"] == "business"
            else anchor["timezone"]
        )
        return {"instant": resolved.isoformat(), "timezone": timezone}
    day = date.fromisoformat(anchor["date"])
    offset = schedule["offset_days"]
    if schedule["day_basis"] == "calendar":
        day += timedelta(days=offset)
    else:
        calendar = calendars.get(schedule["business_calendar_id"])
        if calendar is None:
            raise DomainError(
                "BUSINESS_CALENDAR_MISSING", "Select a known business-day calendar."
            )
        if anchor["timezone"] != calendar["timezone"]:
            raise DomainError(
                "EXACT_TIME_MISSING",
                "A date-only anchor cannot be converted into another calendar timezone.",
            )
        step = 1 if offset >= 0 else -1
        remaining = abs(offset)
        while remaining:
            day += timedelta(days=step)
            if (
                day.weekday() not in calendar["weekend_days"]
                and day.isoformat() not in calendar["holidays"]
            ):
                remaining -= 1
    return {"date": day.isoformat(), "timezone": anchor["timezone"]}
