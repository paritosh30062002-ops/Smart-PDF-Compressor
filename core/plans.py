"""Plans, pricing and quota rules for Smart PDF Compressor.

DEFAULT_PLANS below are the starting values. The admin can change every plan (name, prices, limits,
days, features, visibility) from the Admin -> Plans page; those changes are saved in the database and
applied on top of these defaults on every page load (see apply_plan_settings()).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Asia/Kolkata")  # daily free limit resets at midnight IST
PLAN_DAYS = 30                      # default validity of a Pro plan


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd: int
    period: str                    # "day" (free: limits reset daily) or "month" (pro: limits per plan period)
    pdf_limit: int | None          # PDFs per period, None = unlimited
    file_limit: int | None         # uploaded ZIP/PDF files per period, None = unlimited
    tagline: str
    extras: tuple[str, ...] = field(default_factory=tuple)   # extra feature lines shown on pricing
    popular: bool = False
    price_inr: int = 0             # what Indian customers pay via UPI
    days: int = PLAN_DAYS          # how long a purchase lasts (pro plans)
    visible: bool = True           # shown on the pricing page (pro plans)

    @property
    def period_label(self) -> str:
        """'month' for ~30-day plans, otherwise e.g. '45 days'."""
        return "month" if self.days in (30, 31) else f"{self.days} days"

    @property
    def features(self) -> tuple[str, ...]:
        """Feature lines for pricing cards: limit lines are generated, so they always match the real limits."""
        lines: list[str] = []
        if self.period == "day":
            if self.file_limit is not None:
                lines.append(f"{self.file_limit:,} ZIP / PDF uploads every day")
            else:
                lines.append("Unlimited uploads every day")
            lines.append("Unlimited PDFs per day" if self.pdf_limit is None else f"Up to {self.pdf_limit:,} PDFs per day")
        else:
            lines.append("Unlimited PDFs" if self.pdf_limit is None else f"{self.pdf_limit:,} PDFs per {self.period_label}")
            lines.append("Unlimited ZIP uploads" if self.file_limit is None else f"{self.file_limit:,} uploads per plan period")
            lines.append(f"Valid for {self.days} days")
        return tuple(lines) + tuple(x for x in self.extras if x.strip())


DEFAULT_PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free", name="Free", price_usd=0, price_inr=0, period="day",
        file_limit=5,      # 5 ZIP / PDF uploads per day
        pdf_limit=100,     # safety cap so one huge ZIP can't replace a Pro plan
        tagline="For trying it out",
        extras=("All compression presets", "Resets every midnight (IST)"),
    ),
    "pro_1k": Plan(
        id="pro_1k", name="Pro 1K", price_usd=50, price_inr=4_799, period="month",
        file_limit=None, pdf_limit=1_000, tagline="For regular work",
        extras=("Priority processing",),
    ),
    "pro_3k": Plan(
        id="pro_3k", name="Pro 3K", price_usd=70, price_inr=6_699, period="month",
        file_limit=None, pdf_limit=3_000, tagline="Best value for teams",
        extras=("Priority processing",), popular=True,
    ),
    "pro_unlimited": Plan(
        id="pro_unlimited", name="Unlimited", price_usd=150, price_inr=14_399, period="month",
        file_limit=None, pdf_limit=None, tagline="For heavy, bulk users",
        extras=("Priority processing",),
    ),
}

# Live plans used by every page. Mutated IN PLACE by apply_plan_settings(), so `from core.plans import PLANS`
# keeps working everywhere.
PLANS: dict[str, Plan] = dict(DEFAULT_PLANS)

EDITABLE_FIELDS = ("name", "tagline", "price_inr", "price_usd", "pdf_limit", "file_limit", "days",
                   "extras", "popular", "visible")


def plan_to_dict(plan: Plan) -> dict:
    d = asdict(plan)
    d["extras"] = list(plan.extras)
    return {k: d[k] for k in EDITABLE_FIELDS}


def _coerce(base: Plan, data: dict) -> Plan:
    """Apply a dict of overrides to a plan, ignoring anything invalid."""
    changes = {}
    for key in EDITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        try:
            if key in ("name", "tagline"):
                value = str(value).strip()[:40]
                if key == "name" and not value:
                    continue
            elif key in ("price_inr", "price_usd", "days"):
                value = max(0, int(float(value)))
                if key == "days":
                    value = max(1, min(value, 3650))
            elif key in ("pdf_limit", "file_limit"):
                value = None if value in (None, "", "unlimited") else max(0, int(float(value)))
            elif key == "extras":
                value = tuple(str(x).strip()[:80] for x in (value or []) if str(x).strip())[:8]
            elif key in ("popular", "visible"):
                value = bool(value)
        except (TypeError, ValueError):
            continue
        changes[key] = value
    if base.id == "free":
        changes.update(price_inr=0, price_usd=0, visible=True)
    return replace(base, **changes) if changes else base


def _secrets_overrides() -> dict:
    """Optional [prices] section in Secrets (older way to change prices)."""
    out: dict = {}
    try:
        from core import config
    except Exception:
        return out
    for pid in DEFAULT_PLANS:
        if pid == "free":
            continue
        for fld in ("inr", "usd"):
            raw = config.setting("prices", f"{pid}_{fld}", None)
            if raw not in (None, ""):
                out.setdefault(pid, {})[f"price_{fld}"] = raw
    return out


def apply_plan_settings(saved: dict | None) -> None:
    """Rebuild PLANS = defaults + Secrets [prices] + admin settings saved in the database."""
    plans = dict(DEFAULT_PLANS)
    for source in (_secrets_overrides(), saved or {}):
        for pid, data in source.items():
            if pid in plans and isinstance(data, dict):
                plans[pid] = _coerce(plans[pid], data)
    PLANS.clear()
    PLANS.update(plans)


def visible_plans() -> list[Plan]:
    return [p for p in PLANS.values() if p.id == "free" or p.visible]


apply_plan_settings(None)

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
        started = (expires - timedelta(days=plan.days)) if expires else start_of_today_utc()
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
            when = "today" if self.plan.period == "day" else "in this plan period"
            if self.files_left == 0:
                tail = "Come back tomorrow or upgrade for more." if self.plan.period == "day" else "Upgrade or renew for more."
                return f"You've used all {self.plan.file_limit:,} uploads {when}. {tail}"
            return (f"{self.plan.name} plan: only {self.files_left} upload(s) left {when}, but you selected {n_files}. "
                    "Remove some files or upgrade.")
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
