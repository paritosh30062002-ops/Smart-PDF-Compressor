"""UPI payments: a QR for your UPI ID with the exact plan amount.

QR  ->  upi://pay?pa=<your UPI ID>&pn=<name>&am=<plan amount>&cu=INR&tn=<plan + order number>
The user pays, enters the UTR, you verify it in your bank app and click Activate in Admin.
"""
from __future__ import annotations

import io
import secrets as pysecrets
import time
import urllib.parse

from core import config


class PaymentError(Exception):
    """Raised with a user-friendly message."""


def new_order_ref() -> str:
    # short, readable, unique enough to match a payment in your bank app
    return "SPC" + time.strftime("%y%m%d") + pysecrets.token_hex(3).upper()


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
