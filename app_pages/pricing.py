"""Pricing page: Free vs Pro plans, prices in USD and INR."""
import html

import streamlit as st

from core import config, nav
from core.auth import current_user, profile_and_quota
from core.currency import format_inr, inr_price, usd_to_inr_rate
from core.plans import PLANS
from core.store import get_store
from core.ui import raw_html

user = current_user()
profile, quota = profile_and_quota(user) if user else (None, None)
current_plan_id = quota.plan.id if quota else None
store = get_store()

pending = set()
if user and store:
    try:
        pending = {r["plan"] for r in store.list_upgrade_requests(status="pending", email=user["email"])}
    except Exception:
        pending = set()

raw_html('<div class="auth-hero"><h2>Simple, honest pricing</h2>'
         '<p>Start free. Upgrade when you need to compress more. Every Pro plan runs for 30 days.</p></div>')

cols = st.columns(len(PLANS), gap="medium")
for col, plan in zip(cols, PLANS.values()):
    with col:
        with st.container(key=f"price_{plan.id}"):
            pop = '<span class="price-tag-pop">MOST POPULAR</span>' if plan.popular else ""
            if plan.price_usd == 0:
                amount = '<div class="price-amount">$0 <small>forever</small></div><div class="price-inr">₹0</div>'
            else:
                amount = (f'<div class="price-amount">${plan.price_usd} <small>/ month</small></div>'
                          f'<div class="price-inr">≈ {format_inr(inr_price(plan.price_usd))} / month</div>')
            feats = "".join(f"<li>{html.escape(f)}</li>" for f in plan.features)
            raw_html(f'<div class="price-top"><span class="price-name">{html.escape(plan.name)}</span>{pop}</div>'
                     f'<div class="price-tagline">{html.escape(plan.tagline)}</div>'
                     f'{amount}<ul class="price-features">{feats}</ul>')

            if plan.id == "free":
                if current_plan_id == "free":
                    st.button("Your current plan", key="btn_free", disabled=True, use_container_width=True)
                elif user:
                    st.button("Included", key="btn_free", disabled=True, use_container_width=True)
                elif st.button("Start free", key="btn_free", use_container_width=True):
                    st.switch_page(nav.page("login"))
            else:
                if current_plan_id == plan.id:
                    st.button("Your current plan", key=f"btn_{plan.id}", disabled=True, use_container_width=True)
                elif plan.id in pending:
                    st.button("Request sent ✓", key=f"btn_{plan.id}", disabled=True, use_container_width=True)
                elif st.button(f"Get {plan.name}", key=f"btn_{plan.id}", use_container_width=True,
                               type="primary" if plan.popular else "secondary"):
                    if not user:
                        st.switch_page(nav.page("login"))
                    elif store is None:
                        st.error("Upgrades are not available right now.")
                    else:
                        try:
                            store.create_upgrade_request(user["email"], plan.id)
                            st.session_state["_upgrade_msg"] = plan.name
                            st.rerun()
                        except Exception:
                            st.error("Could not send the request. Please try again.")

if st.session_state.get("_upgrade_msg"):
    contact = config.support_contact()
    extra = f" You can also reach us at {contact}." if contact else ""
    st.success(f"Request for {st.session_state.pop('_upgrade_msg')} received! We'll contact you with payment "
               f"details and activate your plan within 24 hours.{extra}")

rate, live = usd_to_inr_rate()
raw_html(f'<div class="rate-note">INR prices are approximate, at {"today's" if live else "a reference"} rate '
         f'of 1 USD = ₹{rate:.2f}. Final amount is confirmed at payment.</div>')

with st.expander("Frequently asked questions"):
    st.markdown(
        "- **What counts as an upload on Free?** Each ZIP or PDF file you select counts as one upload. "
        "You get 5 per day (up to 100 PDFs), and it resets at midnight IST.\n"
        "- **What counts on Pro?** Every PDF compressed, including PDFs inside ZIP files.\n"
        "- **Are my files stored?** No. Files are processed in a temporary folder and deleted right after "
        "compression. We only keep counts (how many files/PDFs) for your plan limit.\n"
        "- **What happens after 30 days?** Your account goes back to Free until you renew."
    )
