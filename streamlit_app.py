from __future__ import annotations

from datetime import date
from typing import Callable

import streamlit as st

from campaign_store import (
    CHANNELS,
    STATUSES,
    Campaign,
    campaigns_from_csv,
    campaigns_from_json,
    campaigns_to_csv,
    campaigns_to_json,
    utc_now,
    validate_campaign,
)

st.set_page_config(
    page_title="Campaign workspace",
    page_icon="📣",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #667085;
            --brand: #5b5bd6;
            --brand-soft: #eef0ff;
            --surface: #ffffff;
            --line: #e7e9f2;
        }
        .stApp {
            background: linear-gradient(180deg, #f7f8fc 0%, #ffffff 42%);
        }
        [data-testid="stSidebar"] {
            background: #fbfbfe;
            border-right: 1px solid var(--line);
        }
        .hero {
            padding: 0.5rem 0 1.5rem;
        }
        .eyebrow {
            color: var(--brand);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .hero h1 {
            color: var(--ink);
            font-size: clamp(2rem, 4vw, 3.4rem);
            letter-spacing: -0.04em;
            line-height: 1.05;
            margin: 0;
        }
        .hero p {
            color: var(--muted);
            font-size: 1.05rem;
            margin: 0.7rem 0 0;
            max-width: 46rem;
        }
        .section-label {
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 700;
            margin: 0.75rem 0 0.25rem;
        }
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 0.9rem;
            padding: 0.85rem 1rem;
        }
        div[data-testid="stForm"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1rem;
        }
        .hint {
            color: var(--muted);
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialise_state() -> None:
    if "campaigns" not in st.session_state:
        st.session_state.campaigns = []
    if "selected_campaign_id" not in st.session_state:
        st.session_state.selected_campaign_id = ""
    if "flash_message" not in st.session_state:
        st.session_state.flash_message = ""
    if "add_form_version" not in st.session_state:
        st.session_state.add_form_version = 0


def campaign_label(campaign: Campaign) -> str:
    return f"{campaign.name} · {campaign.status}"


def as_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def replace_or_merge_campaigns(imported: list[Campaign], mode: str) -> None:
    if mode == "Replace current list":
        st.session_state.campaigns = imported
        return

    by_id = {campaign.id: campaign for campaign in st.session_state.campaigns}
    for campaign in imported:
        by_id[campaign.id] = campaign
    st.session_state.campaigns = list(by_id.values())


def import_campaign_file(uploaded_file, mode: str) -> tuple[int, int, str]:
    raw = uploaded_file.getvalue().decode("utf-8-sig")
    if uploaded_file.name.lower().endswith(".json"):
        imported = campaigns_from_json(raw)
    else:
        imported = campaigns_from_csv(raw)

    valid: list[Campaign] = []
    invalid_count = 0
    for campaign in imported:
        if validate_campaign(campaign.to_dict()):
            invalid_count += 1
        else:
            valid.append(campaign)

    if valid:
        replace_or_merge_campaigns(valid, mode)
    return len(valid), invalid_count, uploaded_file.name


def render_sidebar() -> tuple[str, list[str], list[str], str]:
    with st.sidebar:
        st.markdown("## Workspace")
        st.caption("Keep planning inputs tidy and ready for review.")

        uploaded_file = st.file_uploader(
            "Import campaigns",
            type=["csv", "json"],
            help="CSV and JSON exports from this workspace can be imported again.",
        )
        import_mode = st.radio(
            "Import behavior",
            ["Merge by campaign ID", "Replace current list"],
            horizontal=True,
        )
        if uploaded_file and st.button("Import file", use_container_width=True):
            try:
                valid_count, invalid_count, file_name = import_campaign_file(
                    uploaded_file, import_mode
                )
                if valid_count:
                    st.success(f"Imported {valid_count} campaign(s) from {file_name}.")
                    if invalid_count:
                        st.warning(
                            f"Skipped {invalid_count} campaign(s) with validation errors."
                        )
                    st.rerun()
                else:
                    st.error("No valid campaigns were found in that file.")
            except (UnicodeDecodeError, ValueError) as exc:
                st.error(str(exc))

        if st.session_state.campaigns:
            csv_bytes = campaigns_to_csv(st.session_state.campaigns).encode("utf-8")
            json_bytes = campaigns_to_json(st.session_state.campaigns).encode("utf-8")
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name="campaigns.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                "Download JSON",
                data=json_bytes,
                file_name="campaigns.json",
                mime="application/json",
                use_container_width=True,
            )

        st.divider()
        st.markdown("### Find campaigns")
        search = st.text_input(
            "Search",
            placeholder="Name, objective, owner or audience",
            label_visibility="collapsed",
        )

        available_statuses = sorted({campaign.status for campaign in st.session_state.campaigns})
        selected_statuses = st.multiselect(
            "Status",
            options=available_statuses or list(STATUSES),
            placeholder="All statuses",
        )

        available_channels = sorted({campaign.channel for campaign in st.session_state.campaigns})
        selected_channels = st.multiselect(
            "Channel",
            options=available_channels or list(CHANNELS),
            placeholder="All channels",
        )

        sort_by = st.selectbox(
            "Sort by",
            ["Recently updated", "Start date", "Budget: high to low", "Name: A–Z"],
        )

    return search, selected_statuses, selected_channels, sort_by


def render_campaign_form(
    campaign: Campaign | None = None,
    *,
    form_key: str,
    on_saved: Callable[[Campaign], None] | None = None,
) -> None:
    editing = campaign is not None
    current = campaign.to_dict() if campaign else {}
    today = date.today()

    with st.form(form_key, clear_on_submit=False):
        st.markdown(
            f'<div class="section-label">{"Edit campaign" if editing else "New campaign"}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Capture the decision-ready details first. You can refine notes and budget later."
        )

        first_row = st.columns([1.6, 1, 1])
        with first_row[0]:
            name = st.text_input(
                "Campaign name *",
                value=current.get("name", ""),
                placeholder="e.g. Q3 product launch",
            )
        with first_row[1]:
            channel = st.selectbox(
                "Channel *",
                options=CHANNELS,
                index=CHANNELS.index(current["channel"])
                if current.get("channel") in CHANNELS
                else 0,
            )
        with first_row[2]:
            status = st.selectbox(
                "Status *",
                options=STATUSES,
                index=STATUSES.index(current["status"])
                if current.get("status") in STATUSES
                else 0,
            )

        second_row = st.columns(2)
        with second_row[0]:
            objective = st.text_area(
                "Objective *",
                value=current.get("objective", ""),
                placeholder="What should this campaign achieve?",
                height=100,
            )
        with second_row[1]:
            audience = st.text_area(
                "Audience *",
                value=current.get("audience", ""),
                placeholder="Who is this campaign for?",
                height=100,
            )

        third_row = st.columns([1, 1, 1])
        with third_row[0]:
            start_date = st.date_input(
                "Start date *",
                value=as_date(current.get("start_date", ""), today),
            )
        with third_row[1]:
            end_date = st.date_input(
                "End date *",
                value=as_date(current.get("end_date", ""), today),
            )
        with third_row[2]:
            budget = st.number_input(
                "Budget",
                min_value=0.0,
                value=float(current.get("budget", 0.0) or 0.0),
                step=100.0,
                format="%.2f",
            )

        owner = st.text_input(
            "Owner *",
            value=current.get("owner", ""),
            placeholder="e.g. Growth team",
        )
        notes = st.text_area(
            "Notes",
            value=current.get("notes", ""),
            placeholder="Add links, dependencies, creative direction or review notes.",
            height=110,
        )

        submitted = st.form_submit_button(
            "Save changes" if editing else "Add campaign",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    payload = {
        **current,
        "name": name,
        "objective": objective,
        "channel": channel,
        "status": status,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "budget": budget,
        "owner": owner,
        "audience": audience,
        "notes": notes,
        "updated_at": utc_now(),
    }
    errors = validate_campaign(payload)
    if errors:
        for error in errors:
            st.error(error)
        return

    saved_campaign = Campaign.from_mapping(payload)
    if editing:
        st.session_state.campaigns = [
            saved_campaign if item.id == saved_campaign.id else item
            for item in st.session_state.campaigns
        ]
        message = f"Updated “{saved_campaign.name}”."
    else:
        st.session_state.campaigns.append(saved_campaign)
        st.session_state.add_form_version += 1
        message = f"Added “{saved_campaign.name}”."

    st.session_state.selected_campaign_id = saved_campaign.id
    st.session_state.flash_message = message
    if on_saved:
        on_saved(saved_campaign)
    st.rerun()


def render_campaign_table(
    campaigns: list[Campaign],
    filtered_campaigns: list[Campaign],
) -> None:
    st.markdown('<div class="section-label">Campaign list</div>', unsafe_allow_html=True)
    st.caption(
        f"Showing {len(filtered_campaigns)} of {len(campaigns)} campaign(s). "
        "Use the selector below the table to edit or remove a campaign."
    )

    if not filtered_campaigns:
        st.info(
            "No campaigns match those filters. Clear a filter or add a new campaign to get started."
        )
        return

    rows = [
        {
            "Campaign": campaign.name,
            "Status": campaign.status,
            "Channel": campaign.channel,
            "Owner": campaign.owner,
            "Audience": campaign.audience,
            "Start": campaign.start_date,
            "End": campaign.end_date,
            "Budget": f"${campaign.budget:,.2f}",
            "Objective": campaign.objective,
        }
        for campaign in filtered_campaigns
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    options = [""] + [campaign.id for campaign in filtered_campaigns]
    selected_id = st.selectbox(
        "Edit a campaign",
        options=options,
        index=options.index(st.session_state.selected_campaign_id)
        if st.session_state.selected_campaign_id in options
        else 0,
        format_func=lambda value: "Choose a campaign…" if not value else campaign_label(
            next(item for item in filtered_campaigns if item.id == value)
        ),
    )
    st.session_state.selected_campaign_id = selected_id

    if selected_id:
        selected = next(item for item in campaigns if item.id == selected_id)
        render_campaign_form(selected, form_key=f"edit_{selected.id}")

        delete_col, _ = st.columns([1, 3])
        with delete_col:
            if st.button("Delete campaign", key=f"delete_{selected.id}"):
                st.session_state.campaigns = [
                    item for item in campaigns if item.id != selected.id
                ]
                st.session_state.selected_campaign_id = ""
                st.session_state.flash_message = f"Deleted “{selected.name}”."
                st.rerun()


def main() -> None:
    apply_styles()
    initialise_state()

    if st.session_state.flash_message:
        st.success(st.session_state.flash_message)
        st.session_state.flash_message = ""

    search, selected_statuses, selected_channels, sort_by = render_sidebar()
    campaigns = list(st.session_state.campaigns)
    query = search.strip().lower()

    filtered_campaigns = [
        campaign
        for campaign in campaigns
        if (
            not query
            or query
            in " ".join(
                [
                    campaign.name,
                    campaign.objective,
                    campaign.owner,
                    campaign.audience,
                    campaign.channel,
                ]
            ).lower()
        )
        and (not selected_statuses or campaign.status in selected_statuses)
        and (not selected_channels or campaign.channel in selected_channels)
    ]

    if sort_by == "Start date":
        filtered_campaigns.sort(key=lambda item: item.start_date)
    elif sort_by == "Budget: high to low":
        filtered_campaigns.sort(key=lambda item: item.budget, reverse=True)
    elif sort_by == "Name: A–Z":
        filtered_campaigns.sort(key=lambda item: item.name.lower())
    else:
        filtered_campaigns.sort(key=lambda item: item.updated_at, reverse=True)

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Campaign operations</div>
            <h1>Campaign workspace</h1>
            <p>Plan, review and keep every campaign input in one calm, searchable place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    active_count = sum(item.status == "Active" for item in campaigns)
    planned_count = sum(item.status == "Planned" for item in campaigns)
    total_budget = sum(item.budget for item in campaigns)
    metrics = st.columns(4)
    metrics[0].metric("Total campaigns", len(campaigns))
    metrics[1].metric("Active", active_count)
    metrics[2].metric("Planned", planned_count)
    metrics[3].metric("Total budget", f"${total_budget:,.0f}")

    list_tab, add_tab = st.tabs(["Campaign list", "Add campaign"])
    with list_tab:
        render_campaign_table(campaigns, filtered_campaigns)
    with add_tab:
        render_campaign_form(
            form_key=f"add_campaign_{st.session_state.add_form_version}"
        )


if __name__ == "__main__":
    main()
