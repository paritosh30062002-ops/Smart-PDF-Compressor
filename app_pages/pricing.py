"""Pricing page: Free vs Pro plans (USD + fixed INR price paid via UPI)."""
import html

import streamlit as st

from core import config, nav
from core.auth import current_user, profile_and_quota
from core.plans import PLANS, visible_plans
from core.store import get_store
from core.ui import raw_html

user = current_user()
store = get_store()

profile, quota = profile_and_quota(user) if user else (None, None)
current_plan_id = quota.plan.id if quota else None

verifying = set()
if user and store:
    try:
        verifying = {o["plan"] for o in store.list_orders(statuses=["submitted"], email=user["email"], limit=20)}
    except Exception:
        verifying = set()


def go_checkout(plan_id: str) -> None:
    st.session_state["checkout_plan"] = plan_id
    st.session_state.pop("checkout_order", None)


raw_html('<div class="auth-hero"><h2>Simple, honest pricing</h2>'
         '<p>Start free. Upgrade when you need to compress more. Pay once with UPI, no auto-renewal.</p></div>')

shown = visible_plans()
cols = st.columns(len(shown), gap="medium")
for col, plan in zip(cols, shown):
    with col:
        with st.container(key=f"price_{plan.id}"):
            pop = '<span class="price-tag-pop">MOST POPULAR</span>' if plan.popular else ""
            if plan.price_usd == 0:
                amount = '<div class="price-amount">$0 <small>forever</small></div><div class="price-inr">₹0</div>'
            else:
                amount = (f'<div class="price-amount">${plan.price_usd} <small>/ {plan.period_label}</small></div>'
                          f'<div class="price-inr">₹{plan.price_inr:,} / {plan.period_label} · pay via UPI</div>')
            feats = "".join(f"<li>{html.escape(f)}</li>" for f in plan.features)
            raw_html(f'<div class="price-top"><span class="price-name">{html.escape(plan.name)}</span>{pop}</div>'
                     f'<div class="price-tagline">{html.escape(plan.tagline)}</div>'
                     f'{amount}<ul class="price-features">{feats}</ul>')

            key = f"btn_{plan.id}"
            if plan.id == "free":
                if current_plan_id == "free":
                    st.button("Your current plan", key=key, disabled=True, use_container_width=True)
                elif user:
                    st.button("Included", key=key, disabled=True, use_container_width=True)
                elif st.button("Start free", key=key, use_container_width=True):
                    st.switch_page(nav.page("login"))
            elif plan.id in verifying:
                st.button("Verifying payment…", key=key, disabled=True, use_container_width=True)
            else:
                label = f"Renew for {plan.days} days" if current_plan_id == plan.id else f"Get {plan.name}"
                if st.button(label, key=key, use_container_width=True,
                             type="primary" if plan.popular else "secondary"):
                    if not user:
                        st.session_state["checkout_plan"] = plan.id
                        st.switch_page(nav.page("login"))
                    else:
                        go_checkout(plan.id)
                        st.switch_page(nav.page("checkout"))

if st.session_state.pop("_checkout_cancelled", False):
    st.toast("Payment cancelled. Nothing was charged.")

mode = config.payment_mode()
note = {
    "upi": "Pay in INR with any UPI app (GPay, PhonePe, Paytm, BHIM). Plans are activated after a quick check.",
    "off": "Online payments are coming soon.",
}[mode]
raw_html(f'<div class="rate-note">{html.escape(note)} USD prices are shown for reference.</div>')

with st.expander("Frequently asked questions"):
    st.markdown(
        "- **What counts as an upload on Free?** Each ZIP or PDF file you select counts as one upload. "
        f"You get {PLANS['free'].file_limit or 'unlimited'} per day, and it resets at midnight IST.\n"
        "- **What counts on Pro?** Every PDF compressed, including PDFs inside ZIP files.\n"
        "- **How do I pay?** Choose a plan, scan the UPI QR with any UPI app and pay the exact amount.\n"
        "- **Are my files stored?** No. Files are processed in a temporary folder and deleted right after "
        "compression. We only keep counts (how many files/PDFs) for your plan limit.\n"
        "- **What happens when my plan ends?** Your account goes back to Free until you renew."
    )
