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


UTR_USED_STATUSES = ("submitted", "paid", "approved")  # a rejected UTR can be submitted again
UTR_USED_MSG = ("This UTR has already been submitted for another order. Check the number, "
                "or contact support if it is your payment.")


def utr_conflict(store, order: dict, statuses: tuple = UTR_USED_STATUSES) -> dict | None:
    """Another order that already uses this order's UTR, if any."""
    utr = (order.get("utr") or "").strip()
    if not utr:
        return None
    return next((o for o in store.orders_with_utr(utr)
                 if o["id"] != order["id"] and o.get("status") in statuses), None)


def _is_duplicate_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "23505" in text or "unique constraint" in text


def submit_utr(store, order: dict, utr: str) -> None:
    """Save the user's UTR on a pending order. One UTR can be used for one order only."""
    utr = utr.strip()
    fresh = store.get_order(order["id"])
    if not fresh or fresh.get("status") != "pending":
        raise PaymentError("This order can no longer be updated. Refresh the page and try again.")
    if utr_conflict(store, {**fresh, "utr": utr}):
        raise PaymentError(UTR_USED_MSG)
    try:
        store.update_order(fresh["id"], status="submitted", utr=utr)
    except Exception as exc:  # database unique index: two people submitted it at the same moment
        if _is_duplicate_error(exc):
            raise PaymentError(UTR_USED_MSG) from exc
        raise


def activate_order(store, order: dict, status: str = "approved") -> None:
    """Give the user the plan for 30 days (idempotent)."""
    fresh = store.get_order(order["id"]) or order
    if fresh.get("status") in ("paid", "approved"):
        return
    used = utr_conflict(store, fresh, ("paid", "approved"))
    if used:
        raise PaymentError(f"Not activated: UTR {fresh['utr']} was already used for order "
                           f"{used.get('order_ref') or used['id']} ({used['email']}).")
    plan = PLANS.get(fresh["plan"])
    store.set_plan(fresh["email"], fresh["plan"], plan.days if plan else PLAN_DAYS)
    store.update_order(fresh["id"], status=status, paid_at=now_utc().isoformat())
