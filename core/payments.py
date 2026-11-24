"""Payments: direct UPI QR (manual verify) and Razorpay UPI QR (automatic).

Direct UPI  -> QR for  upi://pay?pa=<your UPI ID>&am=<plan amount>&tn=<order ref>
               user pays, enters the UTR, you verify in your bank app and click Activate.
Razorpay    -> Razorpay creates a single-use, fixed-amount QR for each order; the app checks
               it every few seconds and activates the plan as soon as the payment is captured.
"""
from __future__ import annotations

import base64
import io
import json
import os
import secrets as pysecrets
import time
import urllib.error
import urllib.parse
import urllib.request

from core import config

QR_MINUTES = 30  # Razorpay single-use QR lifetime (allowed: 2 min .. 2 hours)
RAZORPAY_BASE = os.environ.get("SPC_RAZORPAY_BASE", "https://api.razorpay.com/v1")


class PaymentError(Exception):
    """Raised with a user-friendly message."""


def new_order_ref() -> str:
    # short, readable, unique enough to match a payment in your bank app
    return "SPC" + time.strftime("%y%m%d") + pysecrets.token_hex(3).upper()


# ---------------- direct UPI ----------------
def upi_uri(amount_inr: int, order_ref: str, plan_name: str) -> str:
    params = {
        "pa": config.upi_id(),
        "pn": config.upi_payee_name(),
        "am": f"{amount_inr:.2f}",
        "cu": "INR",
        "tn": f"{plan_name} {order_ref}",
    }
    # keep "@" readable (some UPI apps reject %40) and no "tr" (merchant-only field; can fail for personal UPI IDs)
    return "upi://pay?" + urllib.parse.urlencode(params, quote_via=lambda v, *a, **k: urllib.parse.quote(v, safe="@"))


def qr_png(data: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def valid_utr(utr: str) -> bool:
    utr = utr.strip()
    return utr.isdigit() and len(utr) == 12


# ---------------- Razorpay ----------------
def _rzp_request(method: str, path: str, body: dict | None = None) -> dict:
    keys = config.razorpay_keys()
    if not keys:
        raise PaymentError("Online payments are not configured.")
    token = base64.b64encode(f"{keys[0]}:{keys[1]}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(RAZORPAY_BASE + path, data=data, method=method, headers={
        "Authorization": f"Basic {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode()).get("error", {}).get("description", "")
        except Exception:
            detail = ""
        raise PaymentError(f"Payment service error: {detail or exc.code}") from exc
    except Exception as exc:
        raise PaymentError("Payment service is not reachable right now. Please try again.") from exc


def razorpay_create_qr(amount_inr: int, order_ref: str, plan_name: str, email: str) -> dict:
    return _rzp_request("POST", "/payments/qr_codes", {
        "type": "upi_qr",
        "name": "Smart PDF Compressor",
        "usage": "single_use",
        "fixed_amount": True,
        "payment_amount": int(amount_inr) * 100,  # paise
        "description": f"{plan_name} - {order_ref}",
        "close_by": int(time.time()) + QR_MINUTES * 60,
        "notes": {"order_ref": order_ref, "email": email, "plan": plan_name},
    })


def razorpay_fetch_qr(qr_id: str) -> dict:
    return _rzp_request("GET", f"/payments/qr_codes/{urllib.parse.quote(qr_id)}")


def razorpay_is_paid(qr: dict, amount_inr: int) -> bool:
    return (int(qr.get("payments_count_received") or 0) >= 1
            and int(qr.get("payments_amount_received") or 0) >= int(amount_inr) * 100)
