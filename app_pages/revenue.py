"""Revenue page (admin only): who paid, how many customers, how much, receipts."""
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core import nav
from core.auth import current_user, is_admin
from core.plans import APP_TZ, PLAN_DAYS, PLANS, effective_plan, parse_ts
from core.receipts import PAID_STATUSES, receipt_filename, receipt_pdf
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
    orders = store.list_orders(limit=5000)
    profiles = {p["email"]: p for p in store.list_profiles()}
except Exception as exc:
    st.error(f"Could not load payments: {exc}")
    st.stop()

paid = [o for o in orders if o.get("status") in PAID_STATUSES]
for o in paid:
    o["_paid_dt"] = parse_ts(o.get("paid_at") or o.get("created_at"))

# ---- period filter ----
now = datetime.now(APP_TZ)
ranges = {
    "This month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
    "Last 30 days": now - timedelta(days=30),
    "This year": now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
    "All time": None,
}
f1, _ = st.columns([4, 2])
with f1:
    period = st.radio("Period", list(ranges), horizontal=True, label_visibility="collapsed", key="rev_period")
since = ranges[period]
in_range = [o for o in paid if since is None or (o["_paid_dt"] and o["_paid_dt"] >= since)]

revenue = sum(int(o.get("amount_inr") or 0) for o in in_range)
customers = {o["email"] for o in in_range}
active_pro = sum(1 for p in profiles.values() if effective_plan(p).id != "free")
avg = revenue / len(in_range) if in_range else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"Revenue · {period.lower()}", f"₹{revenue:,}")
m2.metric("Payments", f"{len(in_range):,}")
m3.metric("Paying customers", f"{len(customers):,}")
m4.metric("Active Pro users now", f"{active_pro:,}")

# ---- charts / breakdown ----
c_left, c_right = st.columns([1.6, 1], gap="large")
with c_left:
    st.subheader("Monthly revenue")
    months = []
    cur = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(12):
        months.append(cur)
        cur = (cur - timedelta(days=1)).replace(day=1)
    months.reverse()
    by_month = defaultdict(int)
    for o in paid:
        if o["_paid_dt"]:
            d = o["_paid_dt"].astimezone(APP_TZ)
            by_month[(d.year, d.month)] += int(o.get("amount_inr") or 0)
    chart = pd.DataFrame({"Month": [m.strftime("%b %y") for m in months],
                          "Revenue (₹)": [by_month[(m.year, m.month)] for m in months]})
    st.bar_chart(chart, x="Month", y="Revenue (₹)", color="#7c3aed", height=260, sort=False)  # keep time order
with c_right:
    st.subheader("By plan")
    rows = []
    for pid, plan in PLANS.items():
        if pid == "free":
            continue
        ps = [o for o in in_range if o.get("plan") == pid]
        amt = sum(int(o.get("amount_inr") or 0) for o in ps)
        rows.append({"Plan": plan.name, "Payments": len(ps), "Revenue (₹)": amt,
                     "Share": f"{(amt * 100 / revenue):.0f}%" if revenue else "0%"})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"Average payment: ₹{avg:,.0f}")

# ---- customers ----
st.subheader("Customers")
spent = defaultdict(lambda: [0, 0, None])
for o in in_range:
    s = spent[o["email"]]
    s[0] += 1
    s[1] += int(o.get("amount_inr") or 0)
    s[2] = max(filter(None, [s[2], o["_paid_dt"]])) if (s[2] or o["_paid_dt"]) else None
cust_rows = []
for email, (count, total, last) in sorted(spent.items(), key=lambda kv: -kv[1][1]):
    prof = profiles.get(email, {})
    eff = effective_plan(prof) if prof else PLANS["free"]
    cust_rows.append({
        "Name": prof.get("name") or "",
        "Email": email,
        "Payments": count,
        "Total paid (₹)": total,
        "Current plan": eff.name,
        "Plan valid until": fmt_date(prof.get("plan_expires_at")) if eff.id != "free" else "expired",
        "Last payment": fmt_date(last),
    })
if cust_rows:
    st.dataframe(cust_rows, use_container_width=True, hide_index=True)
else:
    st.caption("No paying customers in this period yet.")

# ---- all payments ----
st.subheader("All payments")
fc1, fc2 = st.columns(2)
with fc1:
    status_labels = {"paid": "Paid", "approved": "Paid (verified)", "submitted": "Waiting for verification",
                     "pending": "Not completed", "rejected": "Rejected", "expired": "Expired",
                     "cancelled": "Cancelled"}
    statuses = st.multiselect("Status", list(status_labels), default=["paid", "approved"],
                              format_func=lambda s: status_labels[s])
with fc2:
    plan_filter = st.multiselect("Plan", [p for p in PLANS if p != "free"], format_func=lambda p: PLANS[p].name)

table = []
for o in orders:
    if statuses and o.get("status") not in statuses:
        continue
    if plan_filter and o.get("plan") not in plan_filter:
        continue
    dt = parse_ts(o.get("paid_at") or o.get("created_at"))
    if since is not None and (dt is None or dt < since):
        continue
    plan = PLANS.get(o.get("plan"))
    paid_dt = parse_ts(o.get("paid_at"))
    table.append({
        "Date": fmt_date(o.get("paid_at") or o.get("created_at")),
        "Customer": (profiles.get(o["email"]) or {}).get("name") or "",
        "Email": o["email"],
        "Plan": plan.name if plan else o.get("plan"),
        "Amount (₹)": int(o.get("amount_inr") or 0),
        "Method": "UPI",
        "Status": status_labels.get(o.get("status"), o.get("status")),
        "Order no.": o.get("order_ref") or str(o["id"]),
        "UTR / Ref": o.get("utr") or o.get("gateway_ref") or "",
        "Valid until": fmt_date(paid_dt + timedelta(days=plan.days if plan else PLAN_DAYS)) if paid_dt else "",
    })
st.dataframe(table, use_container_width=True, hide_index=True)

d1, d2 = st.columns([1, 2.2], vertical_alignment="bottom")
with d1:
    csv = pd.DataFrame(table).to_csv(index=False).encode("utf-8-sig") if table else b""
    st.download_button("Download CSV (Excel)", csv, file_name=f"payments-{now:%Y%m%d}.csv", mime="text/csv",
                       use_container_width=True, disabled=not table)
with d2:
    paid_in_table = [o for o in orders if o.get("status") in PAID_STATUSES
                     and (o.get("order_ref") or str(o["id"])) in {r["Order no."] for r in table}]
    if paid_in_table:
        r1, r2 = st.columns([2, 1], vertical_alignment="bottom")
        with r1:
            pick = st.selectbox("Receipt for", paid_in_table,
                                format_func=lambda o: f"{o.get('order_ref') or o['id']} · {o['email']} · ₹{int(o.get('amount_inr') or 0):,}")
        with r2:
            name = (profiles.get(pick["email"]) or {}).get("name") or ""
            st.download_button("Download receipt", receipt_pdf(pick, name), file_name=receipt_filename(pick),
                               mime="application/pdf", use_container_width=True, key="rcpt_admin")

st.caption("Raw data lives in Supabase → Table Editor → upgrade_requests. "
           "Match each payment with your bank / UPI app statement using the UTR.")
