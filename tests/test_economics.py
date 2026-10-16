from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from packages.domain.economics import (
    cash_metrics,
    freight,
    number,
    convert,
    resolve_schedule,
    validate_allocations,
)
from services.api.store import DomainError

DAY = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)


def events(values):
    return [
        {
            "id": str(i),
            "at": DAY + timedelta(days=day),
            "amount": Decimal(amount),
            "direction": direction,
            "sequence": sequence,
            "kind": kind,
        }
        for i, (day, amount, direction, sequence, kind) in enumerate(values)
    ]


BASE = [
    (0, "32000000", "in", 0, "operating"),
    (0, "50000000", "out", 1, "operating"),
    (14, "78000000", "out", 0, "operating"),
    (24, "6000000", "out", 0, "operating"),
    (54, "128000000", "in", 0, "operating"),
]


class EconomicsTests(unittest.TestCase):
    def test_sub_cent_gap_cannot_round_into_ready_cash(self):
        result, _ = cash_metrics(
            events([(0, ".004", "out", 0, "operating")]), Decimal(0), Decimal(0), "USD"
        )
        self.assertEqual(result["minimum_cash"], "-0.01")
        self.assertEqual(result["peak_cash_gap"], "0.01")
        self.assertEqual(result["buffer_shortfall"], "0.01")
        self.assertEqual(result["required_own_funds"], "0.01")

    def test_golden_baseline_and_timely_late_financing(self):
        result, _ = cash_metrics(
            events(BASE), Decimal("50000000"), Decimal("5000000"), "IDR"
        )
        self.assertEqual(result["minimum_cash"], "-52000000.00")
        self.assertEqual(result["buffer_shortfall"], "57000000.00")
        self.assertEqual(result["required_own_funds"], "107000000.00")
        self.assertEqual(result["final_cash"], "76000000.00")
        loan = [
            (13, "60000000", "in", 0, "loan_draw"),
            (13, "1000000", "out", 1, "finance_cost"),
            (54, "1200000", "out", 1, "finance_cost"),
            (54, "60000000", "out", 2, "principal_repayment"),
        ]
        funded, _ = cash_metrics(
            events(BASE + loan), Decimal("50000000"), Decimal("5000000"), "IDR"
        )
        self.assertEqual(funded["minimum_cash"], "7000000.00")
        self.assertEqual(funded["final_cash"], "73800000.00")
        self.assertEqual(funded["required_own_funds"], "48000000.00")
        late = [(15 if row[0] == 13 else row[0], *row[1:]) for row in loan]
        result, _ = cash_metrics(
            events(BASE + late), Decimal("50000000"), Decimal("5000000"), "IDR"
        )
        self.assertEqual(result["minimum_cash"], "-46000000.00")
        self.assertEqual(result["buffer_shortfall"], "51000000.00")

    def test_buyer_terms_and_late_receipt_goldens(self):
        for deposit, expected, shortfall in [
            ("89600000", "5600000.00", "0.00"),
            ("88000000", "4000000.00", "1000000.00"),
        ]:
            values = list(BASE)
            values[0] = (0, deposit, "in", 0, "operating")
            values[-1] = (
                54,
                str(Decimal("160000000") - Decimal(deposit)),
                "in",
                0,
                "operating",
            )
            result, _ = cash_metrics(
                events(values), Decimal("50000000"), Decimal("5000000"), "IDR"
            )
            self.assertEqual(result["minimum_cash"], expected)
            self.assertEqual(result["buffer_shortfall"], shortfall)
        late = list(BASE)
        late[-1] = (84, *BASE[-1][1:])
        result, _ = cash_metrics(
            events(late), Decimal("50000000"), Decimal("5000000"), "IDR"
        )
        interval = result["negative_intervals"][0]
        self.assertEqual(
            (
                datetime.fromisoformat(interval["end"])
                - datetime.fromisoformat(interval["start"])
            ).days,
            70,
        )

    def test_wm_air_and_fcl_use_explicit_quote_basis(self):
        packages = [
            {"count": 1, "length_cm": "300", "width_cm": "100", "height_cm": "100"}
        ]
        self.assertEqual(
            freight("sea_lcl", packages, "2000", "100", "350"), Decimal(350)
        )
        self.assertEqual(
            freight("air", packages, "200", "2", divisor="6000"), Decimal(1000)
        )
        self.assertEqual(
            freight("sea_fcl", [], "0", "1000", containers="2"), Decimal(2000)
        )
        with self.assertRaises(DomainError):
            freight("air", packages, "200", "2")

    def test_decimal_currency_and_fx_constraints(self):
        for value in [1.2, "NaN", "Infinity", "-2", "1e3", "1\n"]:
            with self.subTest(value=value), self.assertRaises(DomainError):
                number(value)
        fx = [{"base_currency": "USD", "quote_currency": "IDR", "rate": "16000"}]
        self.assertEqual(
            convert({"amount": "2.50", "currency": "USD"}, "IDR", fx), Decimal(40000)
        )
        self.assertEqual(
            convert({"amount": "40000", "currency": "IDR"}, "USD", fx), Decimal("2.5")
        )
        with self.assertRaises(DomainError):
            convert({"amount": "1", "currency": "USD"}, "IDR", [{**fx[0], "rate": "0"}])

    def test_unknown_sequence_uses_debit_first(self):
        rows = events(
            [(0, "10", "in", None, "operating"), (0, "10", "out", None, "operating")]
        )
        result, warnings = cash_metrics(rows, Decimal(0), Decimal(0), "EUR")
        self.assertEqual(result["minimum_cash"], "-10.00")
        self.assertEqual(warnings[0]["code"], "SAME_DAY_SEQUENCE_UNKNOWN")

    def test_business_dates_and_cycles(self):
        anchor = {
            "id": "arrival",
            "forecast": {"instant": "2026-10-16T12:00:00Z", "timezone": "UTC"},
        }
        schedule = {
            "kind": "event_relative",
            "anchor_milestone_id": "arrival",
            "offset_days": 1,
            "day_basis": "business",
            "business_calendar_id": "weekdays",
        }
        calendar = {
            "id": "weekdays",
            "timezone": "UTC",
            "weekend_days": [5, 6],
            "holidays": ["2026-10-19"],
        }
        self.assertEqual(
            resolve_schedule(schedule, {"arrival": anchor}, {"weekdays": calendar})
            .date()
            .isoformat(),
            "2026-10-20",
        )
        with self.assertRaises(DomainError):
            resolve_schedule(schedule, {"arrival": anchor}, {})
        cyclic = {"id": "arrival", "schedule": schedule}
        with self.assertRaises(DomainError):
            resolve_schedule(schedule, {"arrival": cyclic}, {"weekdays": calendar})

    def test_allocation_bounds_and_deduplication(self):
        a = {"line_item_id": "line_1", "shipment_id": None, "fraction": "1"}
        validate_allocations([a])
        for allocations in [
            [a, a],
            [{**a, "fraction": "1.1"}],
            [{**a, "fraction": ".5"}],
            [{**a, "line_item_id": None}],
        ]:
            with self.assertRaises(DomainError):
                validate_allocations(allocations)

    def test_calendar_offsets_preserve_named_zone_across_dst(self):
        anchor = {
            "id": "arrival",
            "actual": None,
            "forecast": {
                "instant": "2026-10-31T12:00:00-04:00",
                "timezone": "America/New_York",
            },
            "agreed": None,
            "proposed": None,
            "schedule": {
                "kind": "fixed",
                "due": {
                    "instant": "2026-10-31T12:00:00-04:00",
                    "timezone": "America/New_York",
                },
            },
        }
        schedule = {
            "kind": "event_relative",
            "anchor_milestone_id": "arrival",
            "offset_days": 2,
            "day_basis": "calendar",
            "business_calendar_id": None,
        }
        self.assertEqual(
            resolve_schedule(schedule, {"arrival": anchor}, {}).isoformat(),
            "2026-11-02T12:00:00-05:00",
        )
