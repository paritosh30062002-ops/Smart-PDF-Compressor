"""Admin page: see users, activate Pro plans, reset usage, delete user data.

Only emails listed in secrets  [app] admin_emails  can open this page.
"""
from collections import defaultdict
from datetime import timedelta

import streamlit as st

from core import nav
from core.auth import current_user, invalidate_profile, is_admin
from core.billing import activate_order
from core.plans import PLAN_DAYS, PLANS, effective_plan, now_utc, parse_ts, start_of_today_utc
from core.store import get_store
from core.ui import fmt_date

user = current_user()
if not user:
    st.switch_page(nav.page("login"))
if not is_admin(user):
    st.error("This page is only for the site admin.")
    st.stop()

store = get_store()
if store is None:
    st.error("Database is not configured.")
    st.stop()

try:
    profiles = store.list_profiles()
    month_rows = store.usage_rows_since(now_utc() - timedelta(days=30))
    to_verify = [o for o in store.list_orders(statuses=["submitted", "pending"])
                 if o["status"] == "submitted" or o.get("method") in (None, "", "manual")]
    recent_paid = store.list_orders(statuses=["paid", "approved"], limit=20)
except Exception as exc:
    st.error(f"Could not load data: {exc}")
    st.stop()

today = start_of_today_utc()
by_user_today = defaultdict(lambda: [0, 0])
by_user_30d = defaultdict(lambda: [0, 0, 0])
for r in month_rows:
    e = r["email"]
    by_user_30d[e][0] += r["files_count"] or 0
    by_user_30d[e][1] += r["pdf_count"] or 0
    by_user_30d[e][2] += max(0, (r["bytes_before"] or 0) - (r["bytes_after"] or 0))
    ts = parse_ts(r["created_at"])
    if ts and ts >= today:
        by_user_today[e][0] += r["files_count"] or 0
        by_user_today[e][1] += r["pdf_count"] or 0

pro_users = sum(1 for p in profiles if effective_plan(p).id != "free")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total users", f"{len(profiles):,}")
m2.metric("Active Pro users", f"{pro_users:,}")
m3.metric("PDFs today", f"{sum(v[1] for v in by_user_today.values()):,}")
m4.metric("Payments to verify", f"{len(to_verify):,}")

# --- Payments to verify (UPI) ---
st.subheader("Payments to verify")
st.caption("Open your bank / UPI app, find the payment by amount and UTR, then click Activate.")
if not to_verify:
    st.caption("Nothing to verify right now.")
for o in to_verify:
    plan = PLANS.get(o["plan"])
    c1, c2, c3 = st.columns([4.2, 1.1, 1.1], vertical_alignment="center")
    utr = o.get("utr") or "—"
    amount = f"₹{int(o['amount_inr']):,}" if o.get("amount_inr") else (f"${plan.price_usd}" if plan else "?")
    c1.markdown(f"**{o['email']}** · {plan.name if plan else o['plan']} · **{amount}**  \n"
                f"UTR `{utr}` · Order `{o.get('order_ref') or o['id']}` · {fmt_date(o['created_at'])}")
    if c2.button("Activate", key=f"act_{o['id']}", type="primary", use_container_width=True):
        activate_order(store, o, "approved")
        invalidate_profile()
        st.toast(f"{o['email']} is now on {plan.name if plan else o['plan']} for {plan.days if plan else PLAN_DAYS} days.")
        st.rerun()
    if c3.button("Reject", key=f"rej_{o['id']}", use_container_width=True):
        store.update_order(o["id"], status="rejected")
        st.rerun()

if recent_paid:
    with st.expander(f"Recent successful payments ({len(recent_paid)})"):
        st.dataframe([{
            "Email": o["email"],
            "Plan": PLANS[o["plan"]].name if o["plan"] in PLANS else o["plan"],
            "Amount (₹)": o.get("amount_inr") or 0,
            "Method": "UPI",
            "Order": o.get("order_ref") or "",
            "UTR": o.get("utr") or "",
            "Paid at": fmt_date(o.get("paid_at") or o.get("created_at")),
        } for o in recent_paid], use_container_width=True, hide_index=True)

# --- Users table ---
st.subheader("Users")
search = st.text_input("Search by email or name", placeholder="type to filter…")
rows = []
for p in profiles:
    if search and search.lower() not in (p["email"] + " " + (p.get("name") or "")).lower():
        continue
    eff = effective_plan(p)
    t = by_user_today[p["email"]]
    m = by_user_30d[p["email"]]
    rows.append({
        "Email": p["email"],
        "Name": p.get("name") or "",
        "Login": p.get("provider") or "",
        "Plan": eff.name,
        "Plan expires": fmt_date(p.get("plan_expires_at")) if eff.id != "free" else "",
        "Uploads today": t[0],
        "PDFs today": t[1],
        "PDFs (30 days)": m[1],
        "MB saved (30 days)": round(m[2] / (1024 * 1024), 1),
        "Last login": fmt_date(p.get("last_login_at")),
        "Joined": fmt_date(p.get("created_at")),
    })
st.dataframe(rows, use_container_width=True, hide_index=True)

# --- Manage one user ---
st.subheader("Manage a user")
emails = [p["email"] for p in profiles]
if not emails:
    st.caption("No users yet.")
    st.stop()
target = st.selectbox("Select user", emails)
prof = next(p for p in profiles if p["email"] == target)
st.caption(f"Current plan: **{effective_plan(prof).name}** · stored plan `{prof.get('plan')}` · "
           f"expires {fmt_date(prof.get('plan_expires_at'))}")

a1, a2, a3 = st.columns(3, gap="medium")
with a1:
    with st.container(key="glasscard_setplan"):
        st.markdown("**Change plan**")
        new_plan = st.selectbox("Plan", list(PLANS), format_func=lambda k: f"{PLANS[k].name} (${PLANS[k].price_usd})",
                                key="adm_plan")
        days = st.number_input("Days valid", min_value=1, max_value=3650, value=PLANS[new_plan].days,
                               key=f"adm_days_{new_plan}", disabled=new_plan == "free")
        if st.button("Apply plan", type="primary", use_container_width=True):
            store.set_plan(target, new_plan, int(days))
            invalidate_profile()
            st.toast(f"{target} → {PLANS[new_plan].name}")
            st.rerun()
with a2:
    with st.container(key="glasscard_reset"):
        st.markdown("**Reset usage**")
        st.caption("Deletes usage history, so limits start again from zero.")
        if st.button("Reset this user", use_container_width=True):
            store.reset_usage(target)
            invalidate_profile()
            st.toast(f"Usage reset for {target}")
            st.rerun()
        all_sure = st.checkbox(f"Yes, reset all {len(profiles)} users", key="adm_reset_all_sure")
        if st.button("Reset all", use_container_width=True, disabled=not all_sure, key="adm_reset_all"):
            store.reset_all_usage()
            invalidate_profile()
            st.toast(f"Usage reset for all {len(profiles)} users")
            st.rerun()
with a3:
    with st.container(key="glasscard_delete"):
        st.markdown("**Delete user data**")
        st.caption("Removes profile, usage and requests. A fresh Free profile is created if they log in again.")
        sure = st.checkbox("Yes, delete permanently", key="adm_sure")
        if st.button("Delete data", use_container_width=True, disabled=not sure):
            store.delete_user_data(target)
            invalidate_profile()
            st.toast(f"Deleted data for {target}")
            st.rerun()
