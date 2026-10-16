import unittest
from packages.domain.planning import local_instant
from services.api.store import DomainError


class LocalPlanningTests(unittest.TestCase):
    def test_owner_zone_and_dst_resolve_without_invented_midnight(self):
        self.assertEqual(
            local_instant("2026-10-16T09:37", "Asia/Jakarta"), "2026-10-16T02:37:00Z"
        )
        self.assertEqual(
            local_instant("2026-11-02T09:37", "America/New_York"),
            "2026-11-02T14:37:00Z",
        )

    def test_nonexistent_ambiguous_and_offset_local_times_need_resolution(self):
        for value in ["2026-03-08T02:30", "2026-11-01T01:30", "2026-10-16T09:37+01:00"]:
            with self.subTest(value=value), self.assertRaises(DomainError) as error:
                local_instant(value, "America/New_York")
            self.assertEqual(error.exception.code, "LOCAL_TIME_UNRESOLVED")
