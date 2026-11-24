"""Loads the admin's plan settings from the database and applies them to PLANS (cached briefly)."""
from __future__ import annotations

import streamlit as st

from core.plans import apply_plan_settings
from core.store import get_store

SETTINGS_KEY = "plans"


@st.cache_data(ttl=30, show_spinner=False)
def _load_saved() -> dict | None:
    store = get_store()
    if store is None:
        return None
    try:
        value = store.get_setting(SETTINGS_KEY)
        return value if isinstance(value, dict) else None
    except Exception:
        return None  # table missing / DB down: fall back to defaults


def refresh_plans() -> None:
    """Call once at the top of every run."""
    apply_plan_settings(_load_saved())


def save_plans(settings: dict) -> None:
    store = get_store()
    store.set_setting(SETTINGS_KEY, settings)
    _load_saved.clear()          # every visitor gets the new plans on their next click
    apply_plan_settings(settings)


def saved_plans() -> dict:
    return dict(_load_saved() or {})
