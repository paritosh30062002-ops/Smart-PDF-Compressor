"""Checkout: pay for a Pro plan with UPI.

A QR for your UPI ID with the exact plan amount; the user pays, submits the UTR, the admin activates.
"""
import html

import streamlit as st

from core import config, nav
from core.auth import current_user, invalidate_profile, profile_and_quota
from core.billing import cancel_order, get_or_create_order, is_current_price
from core.payments import PaymentError, qr_png, upi_uri, valid_utr
from core.plans import PLANS
from core.store import get_store
from core.ui import fmt_date, raw_html

user = current_user()
if not user:
    st.switch_page(nav.page("login"))
if st.session_state.get("_checkout_cancelled"):
    st.switch_page(nav.page("pricing"))

plan_id = st.session_state.get("checkout_plan")
if plan_id not in PLANS or plan_id == "free" or not PLANS[plan_id].visible:
    st.info("Choose a plan first.")
    st.page_link(nav.page("pricing"), label="See plans", icon=":material/workspace_premium:")
    st.stop()

plan = PLANS[plan_id]
store = get_store()
mode = config.payment_mode()
profile, quota = profile_and_quota(user)

if store is None or mode == "off":
    st.warning("Payments are not set up yet. Please contact the site owner.")
    st.stop()

# ---- get (or reuse) the order for this plan ----
order = st.session_state.get("checkout_order")
if not order or order.get("plan") != plan_id or order.get("email") != user["email"]:
    try:
        order = get_or_create_order(store, user["email"], plan_id)
        st.session_state["checkout_order"] = order
    except PaymentError as exc:
        st.error(str(exc))
        st.page_link(nav.page("pricing"), label="Back to pricing", icon=":material/arrow_back:")
        st.stop()
order = store.get_order(order["id"]) or order

# Order not usable any more (price changed by the admin, or cancelled elsewhere) -> make a fresh one
if order.get("status") == "cancelled" or (order.get("status") == "pending" and not is_current_price(order)):
    cancel_order(store, order)
    try:
        order = get_or_create_order(store, user["email"], plan_id)
    except PaymentError as exc:
        st.error(str(exc))
        st.stop()
st.session_state["checkout_order"] = order


def cancel_checkout() -> None:
    cancel_order(store, order)
    st.session_state.pop("checkout_order", None)
    st.session_state.pop("checkout_plan", None)
    st.session_state["_checkout_cancelled"] = True


def cancel_button() -> None:
    if order.get("status") == "pending":
        if st.button("Cancel payment", key="cancel_pay", use_container_width=True, on_click=cancel_checkout):
            st.switch_page(nav.page("pricing"))


left, right = st.columns([1, 1.15], gap="large")

# ---- left: order summary ----
with left:
    with st.container(key="glasscard_summary"):
        feats = "".join(f"<li>{html.escape(f)}</li>" for f in plan.features)
        renew = ""
        if quota and quota.plan.id == plan_id and order.get("status") not in ("paid", "approved"):
            renew = ('<div class="price-tagline" style="margin-top:8px">You already have this plan. Paying again '
                     f'starts a fresh {plan.days}-day period from today.</div>')
        raw_html(
            f'<div class="price-top"><span class="price-name">{html.escape(plan.name)}</span>'
            f'<span class="plan-badge pro">{plan.days} days</span></div>'
            f'<div class="price-tagline">{html.escape(plan.tagline)}</div>'
            f'<div class="price-amount">₹{plan.price_inr:,} <small>/ {plan.period_label}</small></div>'
            f'<div class="price-inr">(${plan.price_usd} USD)</div>'
            f'<ul class="price-features">{feats}</ul>{renew}'
            f'<div class="order-meta">Order <b>{html.escape(order["order_ref"])}</b> · {html.escape(user["email"])}</div>'
        )
    st.page_link(nav.page("pricing"), label="Choose a different plan", icon=":material/arrow_back:")

# ---- right: payment ----
with right:
    with st.container(key="glasscard_pay"):
        status = order.get("status")

        if status in ("paid", "approved"):
            invalidate_profile()
            st.session_state.pop("checkout_plan", None)  # done: don't send the user back here on next login
            raw_html('<div class="pay-title">Payment received ✓</div>'
                     f'<div class="price-tagline">Your {html.escape(plan.name)} plan is active. Enjoy!</div>')
            st.page_link(nav.page("compressor"), label="Start compressing", icon=":material/compress:",
                         use_container_width=True)

        else:  # UPI QR
            uri = upi_uri(int(order["amount_inr"]), order["order_ref"], plan.name)
            raw_html('<div class="pay-title">Scan &amp; pay with any UPI app</div>'
                     '<div class="price-tagline">Pay the exact amount, then enter the 12-digit UTR / '
                     'transaction ID below.</div>')
            with st.container(key="qrbox"):
                st.image(qr_png(uri), width=260)
            raw_html(f'<div class="pay-amount">₹{int(order["amount_inr"]):,}</div>'
                     f'<div class="price-tagline" style="text-align:center">UPI ID: <b>{html.escape(config.upi_id())}</b>'
                     f' · Note: {html.escape(order["order_ref"])}</div>')
            st.link_button("Open UPI app (on phone)", uri, use_container_width=True)

            if status == "submitted":
                st.success(f"Thanks! We're verifying your payment (UTR {order.get('utr')}). "
                           "Your plan will be activated within a few hours.")
            elif status == "rejected":
                st.error("We could not verify this payment. Please contact support with your UTR.")
            else:
                with st.form("utr_form", border=False):
                    utr = st.text_input("UTR / UPI transaction ID (12 digits)", max_chars=12,
                                        placeholder="e.g. 412345678901",
                                        help="Find it in your UPI app under the payment details.")
                    sent = st.form_submit_button("I have paid, submit", type="primary", use_container_width=True)
                if sent:
                    if not valid_utr(utr):
                        st.error("Enter the 12-digit UTR number from your UPI app.")
                    else:
                        store.update_order(order["id"], status="submitted", utr=utr.strip())
                        st.rerun()
                cancel_button()
            contact = config.support_contact()
            if contact:
                st.caption(f"Need help? Contact {contact} with your order number {order['order_ref']}.")
