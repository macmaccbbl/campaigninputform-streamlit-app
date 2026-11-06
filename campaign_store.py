"""Small, integration-friendly campaign data model and serializers.

The Streamlit UI keeps its state in memory, while this module owns the campaign
schema and portable CSV/JSON import/export behavior. That makes it easy to add
a database or API adapter later without changing the form and table UX.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

DATE_FORMAT = "%Y-%m-%d"

CHANNELS = (
    "Email",
    "Paid social",
    "Organic social",
    "Search",
    "Display",
    "Content",
    "Events",
    "Other",
)

STATUSES = (
    "Draft",
    "Planned",
    "Active",
    "Paused",
    "Complete",
)

CAMPAIGN_FIELDS = (
    "id",
    "name",
    "objective",
    "channel",
    "status",
    "start_date",
    "end_date",
    "budget",
    "owner",
    "audience",
    "notes",
    "created_at",
    "updated_at",
)


def utc_now() -> str:
    """Return a compact, timezone-aware timestamp for audit fields."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalise_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    value = _text(value)
    if not value:
        return ""

    try:
        return datetime.strptime(value, DATE_FORMAT).date().isoformat()
    except ValueError:
        return value


def _coerce_budget(value: Any) -> float:
    if value in (None, ""):
        return 0.0

    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Budget must be a number.") from exc

    if amount < 0:
        raise ValueError("Budget cannot be negative.")

    return round(amount, 2)


@dataclass
class Campaign:
    id: str
    name: str
    objective: str
    channel: str
    status: str
    start_date: str
    end_date: str
    budget: float
    owner: str
    audience: str
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "Campaign":
        """Build a campaign from form, CSV, or JSON data."""

        now = utc_now()
        return cls(
            id=_text(row.get("id")) or uuid.uuid4().hex[:10],
            name=_text(row.get("name")),
            objective=_text(row.get("objective")),
            channel=_text(row.get("channel")),
            status=_text(row.get("status")) or "Draft",
            start_date=_normalise_date(row.get("start_date")),
            end_date=_normalise_date(row.get("end_date")),
            budget=_coerce_budget(row.get("budget")),
            owner=_text(row.get("owner")),
            audience=_text(row.get("audience")),
            notes=_text(row.get("notes")),
            created_at=_text(row.get("created_at")) or now,
            updated_at=_text(row.get("updated_at")) or now,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_campaign(row: Mapping[str, Any]) -> list[str]:
    """Return user-facing validation messages for a campaign payload."""

    errors: list[str] = []

    required = {
        "name": "Campaign name",
        "objective": "Objective",
        "channel": "Channel",
        "status": "Status",
        "start_date": "Start date",
        "end_date": "End date",
        "owner": "Owner",
        "audience": "Audience",
    }
    for field, label in required.items():
        if not _text(row.get(field)):
            errors.append(f"{label} is required.")

    start_value = _normalise_date(row.get("start_date"))
    end_value = _normalise_date(row.get("end_date"))
    start_date: date | None = None
    end_date: date | None = None

    if start_value:
        try:
            start_date = datetime.strptime(start_value, DATE_FORMAT).date()
        except ValueError:
            errors.append("Start date must use YYYY-MM-DD format.")

    if end_value:
        try:
            end_date = datetime.strptime(end_value, DATE_FORMAT).date()
        except ValueError:
            errors.append("End date must use YYYY-MM-DD format.")

    if start_date and end_date and end_date < start_date:
        errors.append("End date must be on or after the start date.")

    try:
        budget = float(row.get("budget", 0) or 0)
        if budget < 0:
            errors.append("Budget cannot be negative.")
    except (TypeError, ValueError):
        errors.append("Budget must be a number.")

    channel = _text(row.get("channel"))
    if channel and channel not in CHANNELS:
        errors.append("Choose a supported channel.")

    status = _text(row.get("status"))
    if status and status not in STATUSES:
        errors.append("Choose a supported status.")

    return errors


def campaigns_to_csv(campaigns: Iterable[Campaign]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CAMPAIGN_FIELDS)
    writer.writeheader()
    for campaign in campaigns:
        writer.writerow(campaign.to_dict())
    return output.getvalue()


def campaigns_from_csv(content: str) -> list[Campaign]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("The CSV file does not contain a header row.")

    campaigns: list[Campaign] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            campaigns.append(Campaign.from_mapping(row))
        except ValueError as exc:
            raise ValueError(f"CSV row {row_number}: {exc}") from exc
    return campaigns


def campaigns_to_json(campaigns: Iterable[Campaign]) -> str:
    return json.dumps(
        [campaign.to_dict() for campaign in campaigns],
        indent=2,
        ensure_ascii=False,
    )


def campaigns_from_json(content: str) -> list[Campaign]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("The JSON file is not valid JSON.") from exc

    if isinstance(payload, dict):
        payload = payload.get("campaigns")

    if not isinstance(payload, list):
        raise ValueError("JSON must contain a list of campaigns.")

    campaigns: list[Campaign] = []
    for item_number, item in enumerate(payload, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"JSON item {item_number} must be an object.")
        try:
            campaigns.append(Campaign.from_mapping(item))
        except ValueError as exc:
            raise ValueError(f"JSON item {item_number}: {exc}") from exc
    return campaigns
