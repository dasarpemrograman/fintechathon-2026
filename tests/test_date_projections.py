import unittest
from packages.domain.dates import project
from services.api.store import DomainError


class DateProjectionTests(unittest.TestCase):
    def test_date_only_relative_forecast_preserves_date_without_midnight(self):
        milestones = {
            "arrival": {
                "id": "arrival",
                "schedule": {
                    "kind": "fixed",
                    "due": {"date": "2026-10-16", "timezone": "Asia/Jakarta"},
                },
            },
            "payment": {
                "id": "payment",
                "schedule": {
                    "kind": "event_relative",
                    "anchor_milestone_id": "arrival",
                    "offset_days": 30,
                    "day_basis": "calendar",
                    "business_calendar_id": None,
                },
            },
        }
        self.assertEqual(
            project("payment", milestones, {}),
            {"date": "2026-11-15", "timezone": "Asia/Jakarta"},
        )
        milestones["arrival"]["forecast"] = {
            "date": "2026-10-20",
            "timezone": "Asia/Jakarta",
        }
        self.assertEqual(project("payment", milestones, {})["date"], "2026-11-19")
        self.assertEqual(milestones["arrival"]["schedule"]["due"]["date"], "2026-10-16")

    def test_business_date_requires_a_known_matching_timezone_calendar(self):
        milestones = {
            "anchor": {
                "id": "anchor",
                "schedule": {
                    "kind": "fixed",
                    "due": {"date": "2026-10-16", "timezone": "Asia/Jakarta"},
                },
            },
            "next": {
                "id": "next",
                "schedule": {
                    "kind": "event_relative",
                    "anchor_milestone_id": "anchor",
                    "offset_days": 1,
                    "day_basis": "business",
                    "business_calendar_id": "local",
                },
            },
        }
        calendar = {
            "local": {
                "timezone": "Asia/Jakarta",
                "weekend_days": [5, 6],
                "holidays": ["2026-10-19"],
            }
        }
        self.assertEqual(project("next", milestones, calendar)["date"], "2026-10-20")
        with self.assertRaises(DomainError):
            project("next", milestones, {})
        calendar["local"]["timezone"] = "UTC"
        with self.assertRaises(DomainError):
            project("next", milestones, calendar)
