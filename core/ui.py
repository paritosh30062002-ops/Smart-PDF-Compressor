"""Small HTML helpers shared by pages (all text is escaped)."""
from __future__ import annotations

import html

import streamlit as st

from core.plans import Plan, Quota, parse_ts, APP_TZ


def raw_html(markup: str) -> None:
    if hasattr(st, "html"):
        st.html(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


def plan_badge(plan: Plan) -> str:
    cls = "plan-badge" if plan.id == "free" else "plan-badge pro"
    return f'<span class="{cls}">{html.escape(plan.name)}</span>'


def usage_bar(label: str, used: int, limit: int | None) -> str:
    if limit is None:
        return (f'<div class="usage-box"><div class="usage-head"><span>{html.escape(label)}</span>'
                f'<span><b>{used:,}</b> used · Unlimited</span></div>'
                f'<div class="usage-track"><div class="usage-fill" style="width:100%;opacity:.35"></div></div></div>')
    pct = 0 if limit == 0 else min(100, round(used * 100 / limit))
    full = " full" if used >= limit else ""
    return (f'<div class="usage-box"><div class="usage-head"><span>{html.escape(label)}</span>'
            f'<span><b>{used:,}</b> / {limit:,}</span></div>'
            f'<div class="usage-track"><div class="usage-fill{full}" style="width:{pct}%"></div></div></div>')


def quota_bars(quota: Quota) -> str:
    when = "today" if quota.plan.period == "day" else "this plan period"
    parts = []
    if quota.plan.file_limit is not None:
        parts.append(usage_bar(f"Uploads {when}", quota.files_used, quota.plan.file_limit))
    parts.append(usage_bar(f"PDFs compressed {when}", quota.pdfs_used, quota.plan.pdf_limit))
    return "".join(parts)


def fmt_date(value) -> str:
    dt = parse_ts(value)
    return dt.astimezone(APP_TZ).strftime("%d %b %Y, %I:%M %p") if dt else "—"
