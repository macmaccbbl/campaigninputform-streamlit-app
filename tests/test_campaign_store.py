import unittest

from campaign_store import (
    Campaign,
    campaigns_from_csv,
    campaigns_from_json,
    campaigns_to_csv,
    campaigns_to_json,
    validate_campaign,
)


def sample_campaign() -> Campaign:
    return Campaign.from_mapping(
        {
            "id": "cmp-001",
            "name": "Spring launch",
            "objective": "Drive qualified trials",
            "channel": "Email",
            "status": "Planned",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "budget": 1250,
            "owner": "Growth team",
            "audience": "Trial users",
            "notes": "Coordinate with product launch.",
        }
    )


class CampaignStoreTests(unittest.TestCase):
    def test_valid_campaign_has_no_validation_errors(self) -> None:
        self.assertEqual(validate_campaign(sample_campaign().to_dict()), [])

    def test_date_order_and_required_fields_are_validated(self) -> None:
        errors = validate_campaign(
            {
                "name": "Broken campaign",
                "objective": "",
                "channel": "Email",
                "status": "Planned",
                "start_date": "2026-04-01",
                "end_date": "2026-03-01",
                "owner": "",
                "audience": "Everyone",
                "budget": -1,
            }
        )
        self.assertIn("Objective is required.", errors)
        self.assertIn("Owner is required.", errors)
        self.assertIn("End date must be on or after the start date.", errors)
        self.assertIn("Budget cannot be negative.", errors)

    def test_csv_round_trip_preserves_campaign_fields(self) -> None:
        restored = campaigns_from_csv(campaigns_to_csv([sample_campaign()]))
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].id, "cmp-001")
        self.assertEqual(restored[0].budget, 1250.0)
        self.assertEqual(restored[0].notes, "Coordinate with product launch.")

    def test_json_round_trip_preserves_campaign_fields(self) -> None:
        restored = campaigns_from_json(campaigns_to_json([sample_campaign()]))
        self.assertEqual(restored[0].name, "Spring launch")
        self.assertEqual(restored[0].start_date, "2026-03-01")

    def test_invalid_budget_is_rejected_during_import(self) -> None:
        with self.assertRaisesRegex(ValueError, "Budget must be a number"):
            campaigns_from_json(
                '[{"name": "Bad import", "budget": "not-a-number"}]'
            )


if __name__ == "__main__":
    unittest.main()
