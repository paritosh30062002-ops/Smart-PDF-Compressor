"""Orders: create / reuse a UPI order, cancel it, activate plans."""
from __future__ import annotations

from datetime import timedelta

from core import config
from core.payments import PaymentError, new_order_ref
from core.plans import PLAN_DAYS, PLANS, now_utc, parse_ts

REUSE_HOURS = 24  # an unpaid order (same plan, same price) is reused for this long


def is_current_price(order: dict) -> bool:
    plan = PLANS.get(order.get("plan"))
    return bool(plan) and int(order.get("amount_inr") or 0) == plan.price_inr


def cancel_order(store, order: dict) -> None:
    """Cancel an unpaid order (only 'pending' ones; a submitted UTR stays for the admin to check)."""
    fresh = store.get_order(order["id"]) or order
    if fresh.get("status") == "pending":
        store.update_order(fresh["id"], status="cancelled")


def get_or_create_order(store, email: str, plan_id: str) -> dict:
    """Reuse a recent unpaid order for this plan at the current price, otherwise create a new one."""
    plan = PLANS[plan_id]
    if config.payment_mode() == "off":
        raise PaymentError("Payments are not set up yet. Please contact the site owner.")

    now = now_utc()
    for order in store.list_orders(statuses=["pending"], email=email, limit=20):
        if order.get("plan") != plan_id:
            continue
        if not is_current_price(order):
            cancel_order(store, order)  # price changed since this QR was made -> never reuse it
            continue
        created = parse_ts(order.get("created_at")) or now
        if now - created < timedelta(hours=REUSE_HOURS):
            return order

    return store.create_order(email, plan_id, plan.price_inr, "upi", new_order_ref())


def activate_order(store, order: dict, status: str = "approved") -> None:
    """Give the user the plan for 30 days (idempotent)."""
    fresh = store.get_order(order["id"]) or order
    if fresh.get("status") in ("paid", "approved"):
        return
    plan = PLANS.get(fresh["plan"])
    store.set_plan(fresh["email"], fresh["plan"], plan.days if plan else PLAN_DAYS)
    store.update_order(fresh["id"], status=status, paid_at=now_utc().isoformat())
