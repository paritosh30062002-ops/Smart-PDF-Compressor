"""Reads settings from Streamlit secrets (Cloud) or environment variables (local)."""
from __future__ import annotations

import os

import streamlit as st


def _secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # no secrets.toml at all
        return {}


def setting(section: str, key: str, default=None):
    env_key = f"SPC_{section}_{key}".upper()
    if env_key in os.environ:
        return os.environ[env_key]
    sec = _secrets().get(section)
    if isinstance(sec, dict) or hasattr(sec, "get"):
        try:
            value = sec.get(key)
        except Exception:
            value = None
        if value not in (None, ""):
            return value
    return default


def as_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def demo_mode() -> bool:
    """Local test mode: SQLite instead of Supabase. Never enable on the public site."""
    return as_bool(os.environ.get("SPC_DEMO", "0"))


def supabase_configured() -> bool:
    return bool(setting("supabase", "url") and setting("supabase", "service_key") and setting("supabase", "anon_key"))


def google_configured() -> bool:
    try:
        auth = st.secrets.get("auth")
        return bool(auth and auth.get("google") and auth["google"].get("client_id"))
    except Exception:
        return False


def admin_emails() -> set[str]:
    raw = setting("app", "admin_emails", [])
    if isinstance(raw, str):
        raw = [x for x in raw.replace(";", ",").split(",")]
    return {str(x).strip().lower() for x in raw if str(x).strip()}


def support_contact() -> str:
    return str(setting("app", "support_contact", "") or "")


def allow_folder_export() -> bool:
    # Off by default: on a public server this would write into the SERVER's disk.
    return as_bool(setting("app", "allow_folder_export", "false"))


# ---- payments ----
def upi_id() -> str:
    """Your UPI ID (VPA) for direct UPI QR payments, e.g. yourname@okhdfcbank."""
    return str(setting("payments", "upi_id", "") or "").strip()


def upi_payee_name() -> str:
    return str(setting("payments", "payee_name", "Smart PDF Compressor") or "Smart PDF Compressor").strip()


def razorpay_keys() -> tuple[str, str] | None:
    key_id = str(setting("razorpay", "key_id", "") or "").strip()
    key_secret = str(setting("razorpay", "key_secret", "") or "").strip()
    return (key_id, key_secret) if key_id and key_secret else None


def payment_mode() -> str:
    """'razorpay' (fully automatic), 'upi' (QR + UTR, admin verifies) or 'off'."""
    if razorpay_keys():
        return "razorpay"
    if upi_id():
        return "upi"
    return "off"
