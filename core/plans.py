"""Plans, pricing and quota rules for Smart PDF Compressor.

Change prices / limits here only - every page reads from this file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Asia/Kolkata")  # daily free limit resets at midnight IST
PLAN_DAYS = 30                      # every Pro plan is valid for 30 days


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd: int
    period: str               # "day" (free) or "month" (pro)
    pdf_limit: int | None     # PDFs per period, None = unlimited
    file_limit: int | None    # uploaded ZIP/PDF files per period, None = unlimited
    tagline: str
    features: tuple[str, ...]
    popular: bool = False
    price_inr: int = 0        # what Indian customers pay via UPI (fixed, so the QR amount never changes)


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_usd=0,
        period="day",
        file_limit=5,          # 5 ZIP / PDF uploads per day
        pdf_limit=100,         # safety cap so one huge ZIP can't replace a Pro plan
        tagline="For trying it out",
        features=(
            "5 ZIP / PDF uploads every day",
            "Up to 100 PDFs per day",
            "All compression presets",
            "Resets every midnight (IST)",
        ),
    ),
    "pro_1k": Plan(
        id="pro_1k",
        name="Pro 1K",
        price_usd=50,
        price_inr=4_799,
        period="month",
        file_limit=None,
        pdf_limit=1_000,
        tagline="For regular work",
        features=(
            "1,000 PDFs per month",
            "Unlimited ZIP uploads",
            "Priority processing",
            "Valid for 30 days",
        ),
    ),
    "pro_3k": Plan(
        id="pro_3k",
        name="Pro 3K",
        price_usd=70,
        price_inr=6_699,
        period="month",
        file_limit=None,
        pdf_limit=3_000,
        tagline="Best value for teams",
        features=(
            "3,000 PDFs per month",
            "Unlimited ZIP uploads",
            "Priority processing",
            "Valid for 30 days",
        ),
        popular=True,
    ),
    "pro_unlimited": Plan(
        id="pro_unlimited",
        name="Unlimited",
        price_usd=150,
        price_inr=14_399,
        period="month",
        file_limit=None,
        pdf_limit=None,
        tagline="For heavy, bulk users",
        features=(
            "Unlimited PDFs",
            "Unlimited ZIP uploads",
            "Priority processing",
            "Valid for 30 days",
        ),
    ),
}

PRO_PLAN_IDS = [p for p in PLANS if p != "free"]


def now_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


def start_of_today_utc() -> datetime:
    local_midnight = datetime.now(APP_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(ZoneInfo("UTC"))


def parse_ts(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=ZoneInfo("UTC"))


def effective_plan(profile: dict) -> Plan:
    """The plan the user can use right now (an expired Pro plan falls back to Free)."""
    plan = PLANS.get(profile.get("plan") or "free", PLANS["free"])
    if plan.id == "free":
        return plan
    expires = parse_ts(profile.get("plan_expires_at"))
    if expires is not None and expires <= now_utc():
        return PLANS["free"]
    return plan


def period_start(profile: dict, plan: Plan) -> datetime:
    if plan.id == "free":
        return start_of_today_utc()
    started = parse_ts(profile.get("plan_started_at"))
    if started is None:
        expires = parse_ts(profile.get("plan_expires_at"))
        started = (expires - timedelta(days=PLAN_DAYS)) if expires else start_of_today_utc()
    return started


@dataclass
class Quota:
    plan: Plan
    files_used: int
    pdfs_used: int

    @property
    def files_left(self) -> int | None:
        return None if self.plan.file_limit is None else max(0, self.plan.file_limit - self.files_used)

    @property
    def pdfs_left(self) -> int | None:
        return None if self.plan.pdf_limit is None else max(0, self.plan.pdf_limit - self.pdfs_used)

    def check_upload(self, n_files: int) -> str | None:
        """Error message if this many uploaded files is not allowed, else None."""
        if self.files_left is not None and n_files > self.files_left:
            if self.files_left == 0:
                return (f"You've used all {self.plan.file_limit} free uploads for today. "
                        "Come back tomorrow or upgrade to Pro for more.")
            return (f"Free plan: only {self.files_left} upload(s) left today, but you selected {n_files}. "
                    "Remove some files or upgrade to Pro.")
        if self.pdfs_left == 0:
            return self._pdf_limit_message()
        return None

    def check_pdfs(self, n_pdfs: int) -> str | None:
        if self.pdfs_left is not None and n_pdfs > self.pdfs_left:
            if self.pdfs_left == 0:
                return self._pdf_limit_message()
            return (f"This job has {n_pdfs} PDFs but your {self.plan.name} plan has only "
                    f"{self.pdfs_left} PDF(s) left this {self.plan.period}. Upgrade for a bigger limit.")
        return None

    def _pdf_limit_message(self) -> str:
        when = "today" if self.plan.period == "day" else "for this plan period"
        return f"You've reached your {self.plan.name} limit of {self.plan.pdf_limit:,} PDFs {when}. Upgrade to continue."
