"""PDF payment receipts (one per paid order)."""
from __future__ import annotations

import io
from datetime import timedelta

from core import config
from core.plans import APP_TZ, PLAN_DAYS, PLANS, parse_ts

PAID_STATUSES = ("paid", "approved")


def _d(value) -> str:
    dt = parse_ts(value)
    return dt.astimezone(APP_TZ).strftime("%d %b %Y") if dt else "-"


def _dt(value) -> str:
    dt = parse_ts(value)
    return dt.astimezone(APP_TZ).strftime("%d %b %Y, %I:%M %p IST") if dt else "-"


def receipt_filename(order: dict) -> str:
    return f"receipt-{order.get('order_ref') or order['id']}.pdf"


def receipt_pdf(order: dict, customer_name: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    plan = PLANS.get(order.get("plan"))
    plan_name = plan.name if plan else str(order.get("plan"))
    paid_at = order.get("paid_at") or order.get("created_at")
    start = parse_ts(paid_at)
    valid_to = _d(start + timedelta(days=PLAN_DAYS)) if start else "-"
    amount = int(order.get("amount_inr") or 0)
    method = "UPI via Razorpay" if order.get("method") == "razorpay" else "UPI"
    ref = order.get("utr") or order.get("gateway_ref") or "-"
    business = str(config.setting("app", "business_name", "Smart PDF Compressor"))
    contact = config.support_contact()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    ink, muted, accent = colors.HexColor("#0f172a"), colors.HexColor("#64748b"), colors.HexColor("#4f46e5")

    # header band
    c.setFillColor(accent)
    c.rect(0, H - 38 * mm, W, 38 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, H - 20 * mm, business)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, H - 27 * mm, "PDF & ZIP compression")
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(W - 20 * mm, H - 20 * mm, "PAYMENT RECEIPT")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 20 * mm, H - 27 * mm, f"No. {order.get('order_ref') or order['id']}")

    # parties + meta
    y = H - 54 * mm
    c.setFillColor(muted); c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "BILLED TO")
    c.drawString(115 * mm, y, "PAYMENT DETAILS")
    c.setFillColor(ink); c.setFont("Helvetica", 11)
    lines_left = [customer_name or order.get("email", ""), order.get("email", "")] if customer_name else [order.get("email", "")]
    for i, line in enumerate(lines_left):
        c.drawString(20 * mm, y - (6 + i * 5.5) * mm, line)
    meta = [("Date", _dt(paid_at)), ("Method", method), ("Reference", ref), ("Status", "Paid")]
    for i, (k, v) in enumerate(meta):
        yy = y - (6 + i * 5.5) * mm
        c.setFillColor(muted); c.setFont("Helvetica", 10); c.drawString(115 * mm, yy, k)
        c.setFillColor(ink); c.setFont("Helvetica-Bold", 10); c.drawString(140 * mm, yy, str(v)[:32])

    # items table
    y = H - 96 * mm
    c.setFillColor(colors.HexColor("#eef2ff"))
    c.rect(20 * mm, y - 2 * mm, W - 40 * mm, 9 * mm, stroke=0, fill=1)
    c.setFillColor(ink); c.setFont("Helvetica-Bold", 10)
    c.drawString(24 * mm, y + 1 * mm, "Description")
    c.drawString(96 * mm, y + 1 * mm, "Period")
    c.drawRightString(W - 24 * mm, y + 1 * mm, "Amount")
    y -= 12 * mm
    c.setFont("Helvetica", 10.5)
    c.drawString(24 * mm, y, f"{plan_name} plan - 30 days")
    c.drawString(96 * mm, y, f"{_d(paid_at)} - {valid_to}")
    c.drawRightString(W - 24 * mm, y, f"INR {amount:,.2f}")
    if plan:
        c.setFillColor(muted); c.setFont("Helvetica", 9)
        limit = "Unlimited PDFs" if plan.pdf_limit is None else f"{plan.pdf_limit:,} PDFs per month"
        c.drawString(24 * mm, y - 5 * mm, limit)
    c.setStrokeColor(colors.HexColor("#e2e8f0")); c.line(20 * mm, y - 10 * mm, W - 20 * mm, y - 10 * mm)

    # total
    y -= 20 * mm
    c.setFillColor(ink); c.setFont("Helvetica-Bold", 12)
    c.drawString(118 * mm, y, "Total paid")
    c.setFillColor(accent); c.setFont("Helvetica-Bold", 14)
    c.drawRightString(W - 24 * mm, y, f"INR {amount:,.2f}")

    # footer
    c.setFillColor(muted); c.setFont("Helvetica", 9)
    c.drawString(20 * mm, 30 * mm, "Thank you for your purchase!")
    c.drawString(20 * mm, 25 * mm, "This is a payment receipt, not a GST tax invoice.")
    if contact:
        c.drawString(20 * mm, 20 * mm, f"Questions? Contact {contact}")
    c.showPage()
    c.save()
    return buf.getvalue()
