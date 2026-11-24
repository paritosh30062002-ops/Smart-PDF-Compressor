"""Admin page: see users, activate Pro plans, reset usage, delete user data.

Only emails listed in secrets  [app] admin_emails  can open this page.
"""
from collections import defaultdict
from datetime import timedelta

import streamlit as st

from core import nav
from core.auth import current_user, invalidate_profile, is_admin
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
    pending = store.list_upgrade_requests(status="pending")
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
m4.metric("Pending upgrade requests", f"{len(pending):,}")

# --- Upgrade requests ---
st.subheader("Upgrade requests")
if not pending:
    st.caption("No pending requests.")
for req in pending:
    plan = PLANS.get(req["plan"])
    c1, c2, c3 = st.columns([4, 1.2, 1.2], vertical_alignment="center")
    c1.markdown(f"**{req['email']}** wants **{plan.name if plan else req['plan']}** "
                f"(${plan.price_usd if plan else '?'}) · {fmt_date(req['created_at'])}")
    if c2.button("Activate", key=f"act_{req['id']}", type="primary", use_container_width=True):
        store.set_plan(req["email"], req["plan"], PLAN_DAYS)
        store.set_request_status(req["id"], "approved")
        invalidate_profile()
        st.toast(f"{req['email']} is now on {plan.name if plan else req['plan']} for {PLAN_DAYS} days.")
        st.rerun()
    if c3.button("Reject", key=f"rej_{req['id']}", use_container_width=True):
        store.set_request_status(req["id"], "rejected")
        st.rerun()

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
        days = st.number_input("Days valid", min_value=1, max_value=365, value=PLAN_DAYS, key="adm_days",
                               disabled=new_plan == "free")
        if st.button("Apply plan", type="primary", use_container_width=True):
            store.set_plan(target, new_plan, int(days))
            invalidate_profile()
            st.toast(f"{target} → {PLANS[new_plan].name}")
            st.rerun()
with a2:
    with st.container(key="glasscard_reset"):
        st.markdown("**Reset usage**")
        st.caption("Deletes this user's usage history, so their limits start again from zero.")
        if st.button("Reset usage", use_container_width=True):
            store.reset_usage(target)
            invalidate_profile()
            st.toast(f"Usage reset for {target}")
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
