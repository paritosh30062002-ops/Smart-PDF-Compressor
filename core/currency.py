"""USD -> INR conversion for the pricing page (live rate, cached, with a safe fallback)."""
from __future__ import annotations

import json
import urllib.request

import streamlit as st

FALLBACK_USD_INR = 96.0  # used only if the live rate can't be fetched
RATE_URL = "https://open.er-api.com/v6/latest/USD"


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def usd_to_inr_rate() -> tuple[float, bool]:
    """Returns (rate, is_live). Cached for 6 hours."""
    try:
        with urllib.request.urlopen(RATE_URL, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rate = float(data["rates"]["INR"])
        if 50 < rate < 200:  # sanity check
            return rate, True
    except Exception:
        pass
    return FALLBACK_USD_INR, False


def inr_price(usd: int) -> int:
    rate, _ = usd_to_inr_rate()
    return int(round(usd * rate / 10.0) * 10)  # round to nearest ₹10


def format_inr(amount: int) -> str:
    """Indian digit grouping: 1,23,456"""
    s = str(int(amount))
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])
