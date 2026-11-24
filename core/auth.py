"""Who is logged in: Google (Streamlit st.login) or email/password (Supabase Auth)."""
from __future__ import annotations

import time

import streamlit as st

from core import config
from core.plans import Quota, effective_plan, period_start
from core.store import StoreError, get_store

PROFILE_TTL = 60  # seconds a cached profile/quota is trusted before re-reading the DB


def _google_user() -> dict | None:
    if not config.google_configured():
        return None
    try:
        if st.user.is_logged_in:
            email = (st.user.get("email") or "").lower()
            if email:
                return {"email": email, "name": st.user.get("name") or email.split("@")[0], "provider": "google"}
    except Exception:
        pass
    return None


def current_user() -> dict | None:
    user = _google_user() or st.session_state.get("email_user")
    if not user:
        return None
    # first time this session: create / update the profile row once
    if st.session_state.get("_profile_synced_for") != user["email"]:
        store = get_store()
        if store is not None:
            try:
                store.upsert_profile(user["email"], name=user.get("name"), provider=user.get("provider"))
                st.session_state["_profile_synced_for"] = user["email"]
            except Exception:
                pass  # DB temporarily down: the user can still browse; quota checks will report it
    return user


def is_admin(user: dict | None) -> bool:
    return bool(user) and user["email"].lower() in config.admin_emails()


def login_email(email: str, password: str) -> None:
    store = get_store()
    if store is None:
        raise StoreError("Login is not configured yet (Supabase secrets missing).")
    user = store.sign_in(email.strip().lower(), password)
    st.session_state["email_user"] = user
    invalidate_profile()


def signup_email(name: str, email: str, phone: str, password: str) -> str:
    store = get_store()
    if store is None:
        raise StoreError("Sign up is not configured yet (Supabase secrets missing).")
    result = store.sign_up(email.strip().lower(), password, name.strip(), phone.strip())
    if result == "ok":
        st.session_state["email_user"] = {"email": email.strip().lower(), "name": name.strip(), "provider": "email"}
        invalidate_profile()
    return result


def logout() -> None:
    google = _google_user() is not None
    for key in ("email_user", "_profile_synced_for", "_profile_cache", "result_bundle"):
        st.session_state.pop(key, None)
    st.session_state["terminal_logs"] = []
    if google:
        st.logout()
    else:
        st.rerun()


def invalidate_profile() -> None:
    st.session_state.pop("_profile_cache", None)


def profile_and_quota(user: dict, force: bool = False) -> tuple[dict, Quota] | tuple[None, None]:
    """Current profile + quota, cached for PROFILE_TTL seconds per session."""
    cache = st.session_state.get("_profile_cache")
    if (not force and cache and cache["email"] == user["email"]
            and time.time() - cache["at"] < PROFILE_TTL):
        return cache["profile"], cache["quota"]
    store = get_store()
    if store is None:
        return None, None
    try:
        profile = store.get_profile(user["email"]) or store.upsert_profile(
            user["email"], name=user.get("name"), provider=user.get("provider"))
        plan = effective_plan(profile)
        files_used, pdfs_used = store.usage_since(user["email"], period_start(profile, plan))
    except Exception:
        return None, None
    quota = Quota(plan=plan, files_used=files_used, pdfs_used=pdfs_used)
    st.session_state["_profile_cache"] = {"email": user["email"], "at": time.time(),
                                          "profile": profile, "quota": quota}
    return profile, quota
