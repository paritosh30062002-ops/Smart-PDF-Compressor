"""Smart PDF Compressor - entry point.

Run locally:            streamlit run streamlit_app.py
Local test (no setup):  SPC_DEMO=1 SPC_APP_ADMIN_EMAILS=you@example.com streamlit run streamlit_app.py
"""
import html

import streamlit as st
from streamlit.runtime.scriptrunner import StopException

from app_pages import legal
from core import config, nav
from core.auth import current_user, is_admin, logout, profile_and_quota
from core.plan_settings import refresh_plans
from core.store import get_store
from core.theme import apply_glass_theme, signal_app_ready
from core.ui import plan_badge, raw_html

st.set_page_config(
    page_title="Smart PDF Compressor",
    page_icon=":page_facing_up:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark Glass"


def on_theme_change() -> None:
    st.session_state.theme_mode = st.session_state.theme_radio


apply_glass_theme(st.session_state.theme_mode)
refresh_plans()  # admin-edited plans (prices, limits, ...) from the database

user = current_user()
admin = is_admin(user)

# --- Pages ---
pages = {
    "compressor": st.Page("app_pages/compressor.py", title="Compressor", icon=":material/compress:",
                          url_path="compressor", default=True),
    "pricing": st.Page("app_pages/pricing.py", title="Pricing", icon=":material/workspace_premium:", url_path="pricing"),
    "account": st.Page("app_pages/account.py", title="Account", icon=":material/person:", url_path="account"),
    "admin": st.Page("app_pages/admin.py", title="Admin", icon=":material/admin_panel_settings:", url_path="admin"),
    "login": st.Page("app_pages/login.py", title="Login", icon=":material/login:", url_path="login"),
    "plans": st.Page("app_pages/plans_admin.py", title="Plans", icon=":material/tune:", url_path="plans"),
    "revenue": st.Page("app_pages/revenue.py", title="Revenue", icon=":material/payments:", url_path="revenue"),
    "checkout": st.Page("app_pages/checkout.py", title="Checkout", icon=":material/shopping_cart:", url_path="checkout"),
    "terms": st.Page(legal.terms, title="Terms", icon=":material/gavel:", url_path="terms"),
    "privacy": st.Page(legal.privacy, title="Privacy", icon=":material/shield:", url_path="privacy"),
    "refund": st.Page(legal.refund, title="Refunds", icon=":material/currency_rupee:", url_path="refund"),
}
nav.register(pages)
current = st.navigation(list(pages.values()), position="hidden")

# --- Shared header ---
h_title, h_theme, h_user = st.columns([4.2, 1.7, 1.5], vertical_alignment="center")
with h_title:
    st.markdown(
        "<div class='hero-wrap'><h1 class='hero-title'>Smart PDF Compressor"
        "<span class='hero-badge'>PRO</span></h1></div>",
        unsafe_allow_html=True,
    )
    st.caption("Shrink PDFs and ZIP archives in seconds, with sharp quality, batch processing and one-click download.")
with h_theme:
    st.radio(
        "Theme",
        ["Dark Glass", "Light Glass"],
        index=0 if st.session_state.theme_mode == "Dark Glass" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="theme_radio",
        on_change=on_theme_change,
    )
with h_user:
    if user:
        profile, quota = profile_and_quota(user)
        badge = plan_badge(quota.plan) if quota else ""
        raw_html(f'<div class="user-chip"><b>{html.escape(user["name"])}</b>{badge}</div>')
        st.button("Log out", on_click=logout, use_container_width=True, key="logout_btn")
    else:
        if st.button("Log in", use_container_width=True, key="header_login"):
            st.switch_page(pages["login"])

with st.container(key="topnav"):
    links = ["compressor", "pricing", "account"] + (["admin", "plans", "revenue"] if admin else []) if user else ["login", "pricing"]
    cols = st.columns(max(6, len(links)))
    for col, name in zip(cols, links):
        with col:
            state = "navon" if pages[name].url_path == current.url_path else "navoff"
            with st.container(key=f"{state}_{name}"):
                st.page_link(pages[name], use_container_width=True)

st.markdown("<hr style='margin:0.45rem 0 0.9rem 0;'>", unsafe_allow_html=True)

if config.demo_mode() and not config.supabase_configured():
    raw_html('<div class="demo-banner">Local demo mode: data is saved in a local SQLite file, '
             'Google login is off. Do not use this mode on the public site.</div>')
elif get_store() is None:
    st.warning("Setup needed: add your Supabase keys in Secrets (see README). Login and plans are disabled until then.")

try:
    current.run()
except StopException:
    pass  # the page used st.stop(): still show the footer and reveal the UI

# --- Footer: legal links on every page ---
st.markdown("<hr style='margin:1.6rem 0 0.4rem 0;'>", unsafe_allow_html=True)
with st.container(key="legalfooter", horizontal=True, horizontal_alignment="center"):
    for name in ("terms", "privacy", "refund"):
        st.page_link(pages[name], width="content")

# --- Reveal the fully rendered UI in one smooth fade (keep this as the last line) ---
signal_app_ready()
