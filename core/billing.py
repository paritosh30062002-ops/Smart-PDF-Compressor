"""Orders: create / reuse, check Razorpay status, activate plans."""
from __future__ import annotations

from datetime import timedelta

from core import config
from core.payments import (QR_MINUTES, PaymentError, new_order_ref, razorpay_create_qr, razorpay_fetch_qr,
                           razorpay_is_paid)
from core.plans import PLAN_DAYS, PLANS, now_utc, parse_ts

REUSE_UPI_HOURS = 24


def get_or_create_order(store, email: str, plan_id: str) -> dict:
    """Reuse a still-valid pending order for this plan, otherwise create a new one."""
    plan = PLANS[plan_id]
    mode = config.payment_mode()
    if mode == "off":
        raise PaymentError("Payments are not set up yet. Please contact the site owner.")

    now = now_utc()
    for order in store.list_orders(statuses=["pending"], email=email, limit=20):
        if order.get("plan") != plan_id or order.get("method") != mode:
            continue
        created = parse_ts(order.get("created_at")) or now
        if mode == "razorpay" and now - created < timedelta(minutes=QR_MINUTES - 3) and order.get("gateway_ref"):
            return order
        if mode == "upi" and now - created < timedelta(hours=REUSE_UPI_HOURS):
            return order

    ref = new_order_ref()
    if mode == "razorpay":
        qr = razorpay_create_qr(plan.price_inr, ref, plan.name, email)
        return store.create_order(email, plan_id, plan.price_inr, "razorpay", ref,
                                  gateway_ref=qr.get("id", ""), qr_url=qr.get("image_url", ""))
    return store.create_order(email, plan_id, plan.price_inr, "upi", ref)


def activate_order(store, order: dict, status: str = "paid") -> None:
    """Give the user the plan for 30 days (idempotent)."""
    fresh = store.get_order(order["id"]) or order
    if fresh.get("status") in ("paid", "approved"):
        return
    store.set_plan(fresh["email"], fresh["plan"], PLAN_DAYS)
    store.update_order(fresh["id"], status=status, paid_at=now_utc().isoformat())


def check_razorpay_order(store, order: dict) -> str:
    """Returns 'paid', 'pending' or 'expired'. Activates the plan when paid."""
    if order.get("status") in ("paid", "approved"):
        return "paid"
    if order.get("method") != "razorpay" or not order.get("gateway_ref"):
        return order.get("status") or "pending"
    qr = razorpay_fetch_qr(order["gateway_ref"])
    if razorpay_is_paid(qr, int(order.get("amount_inr") or 0)):
        activate_order(store, order, "paid")
        return "paid"
    if qr.get("status") == "closed":
        store.update_order(order["id"], status="expired")
        return "expired"
    return "pending"


def settle_pending_razorpay(store, email: str) -> bool:
    """Catch payments made after the user closed the checkout tab. True if a plan got activated."""
    if config.payment_mode() != "razorpay":
        return False
    activated = False
    for order in store.list_orders(statuses=["pending"], email=email, limit=10):
        if order.get("method") != "razorpay":
            continue
        try:
            activated = check_razorpay_order(store, order) == "paid" or activated
        except PaymentError:
            pass
    return activated
