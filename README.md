# Campaign workspace

A focused Streamlit workspace for planning, reviewing, and maintaining a campaign list.

## What it includes

- Structured campaign form with required-field validation, date-range checks, and budget validation.
- Responsive layout with campaign metrics and clear empty states.
- Search across campaign name, objective, owner, audience, and channel.
- Status and channel filters plus useful sorting options.
- In-place campaign editing and deletion from the campaign list.
- Portable CSV and JSON import/export from the sidebar.
- A small, integration-friendly data model in `campaign_store.py`, keeping storage concerns separate from the UI.

The app currently stores data in the Streamlit session, so a refresh starts a new list. CSV and JSON import/export provide a simple handoff while a database or API integration is added later.

## Run locally

Prerequisite: install `uv`.

    uv sync
    uv run streamlit run streamlit_app.py

## Test

    python -m unittest discover -s tests -v

## Project structure

- `streamlit_app.py` — Streamlit presentation layer and user interactions.
- `campaign_store.py` — Campaign schema, validation, and CSV/JSON serializers.
- `tests/` — Standard-library unit tests for the campaign data layer.
