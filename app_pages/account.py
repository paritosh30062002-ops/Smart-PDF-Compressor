"""Account page: profile, current plan, usage, edit details."""
import html

import streamlit as st

from core import nav
from core.auth import current_user, invalidate_profile, logout, profile_and_quota
from core.billing import settle_pending_razorpay
from core.receipts import PAID_STATUSES, receipt_filename, receipt_pdf
from core.plans import PLANS
from core.store import get_store
from core.ui import fmt_date, plan_badge, quota_bars, raw_html

user = current_user()
if not user:
    st.switch_page(nav.page("login"))

store = get_store()
if store is not None:
    try:
        settle_pending_razorpay(store, user["email"])
    except Exception:
        pass
profile, quota = profile_and_quota(user, force=True)
if profile is None:
    st.error("Account service is not reachable right now. Please try again in a minute.")
    st.stop()

left, right = st.columns([1.1, 1], gap="large")

with left:
    with st.container(key="glasscard_profile"):
        provider = "Google" if profile.get("provider") == "google" else "Email & password"
        raw_html(
            f'<div class="price-top"><span class="price-name">{html.escape(profile.get("name") or "")}</span>'
            f'{plan_badge(quota.plan)}</div>'
            f'<div class="price-tagline">{html.escape(user["email"])} · {provider}</div>'
            f'<div class="price-tagline">Member since {fmt_date(profile.get("created_at"))}</div>'
        )
        st.write("")
        with st.form("profile_form", border=False):
            name = st.text_input("Full name", value=profile.get("name") or "")
            phone = st.text_input("Phone", value=profile.get("phone") or "")
            if st.form_submit_button("Save changes", use_container_width=True):
                try:
                    store.update_profile(user["email"], name=name.strip(), phone=phone.strip())
                    if st.session_state.get("email_user"):
                        st.session_state["email_user"]["name"] = name.strip()
                    invalidate_profile()
                    st.success("Saved.")
                except Exception:
                    st.error("Could not save right now.")
        st.button("Log out", on_click=logout, key="logout_account", use_container_width=True)

with right:
    with st.container(key="glasscard_plan"):
        plan = quota.plan
        stored_plan = PLANS.get(profile.get("plan") or "free", PLANS["free"])
        if plan.id == "free":
            sub = "Free plan · resets every midnight (IST)"
            if stored_plan.id != "free":
                sub = f"Your {stored_plan.name} plan expired on {fmt_date(profile.get('plan_expires_at'))}"
        else:
            sub = f"Active until {fmt_date(profile.get('plan_expires_at'))}"
        raw_html(f'<div class="price-top"><span class="price-name">Your plan: {html.escape(plan.name)}</span></div>'
                 f'<div class="price-tagline">{html.escape(sub)}</div><div style="height:14px"></div>'
                 + quota_bars(quota))
        st.page_link(nav.page("pricing"), label="Upgrade or renew", icon=":material/workspace_premium:",
                     use_container_width=True)

        try:
            orders = store.list_orders(email=user["email"], limit=5)
        except Exception:
            orders = []
        if orders:
            st.caption("Your payments")
            labels = {"pending": "awaiting payment", "submitted": "verifying", "paid": "paid ✓",
                      "approved": "paid ✓", "rejected": "rejected", "expired": "expired"}
            for o in orders:
                name_ = PLANS[o["plan"]].name if o["plan"] in PLANS else o["plan"]
                amt = f" · ₹{int(o['amount_inr']):,}" if o.get("amount_inr") else ""
                row_l, row_r = st.columns([3, 1.2], vertical_alignment="center")
                row_l.caption(f"• {name_}{amt} — {labels.get(o['status'], o['status'])} "
                              f"({fmt_date(o.get('paid_at') or o['created_at'])})")
                if o.get("status") in PAID_STATUSES:
                    row_r.download_button("Receipt", receipt_pdf(o, profile.get("name") or ""),
                                          file_name=receipt_filename(o), mime="application/pdf",
                                          key=f"rcpt_{o['id']}", use_container_width=True)
