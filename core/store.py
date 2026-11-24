"""Database layer.

SupabaseStore -> real database (used on the live site).
LocalStore    -> SQLite file, only for local testing with SPC_DEMO=1.

Both expose the same methods, so the pages never care which one is active.
Only small numbers are stored (who, plan, how many files/PDFs) - never the PDFs themselves.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets as pysecrets
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from core import config
from core.plans import PLAN_DAYS, now_utc


class StoreError(Exception):
    """Raised with a user-friendly message."""


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# --------------------------------------------------------------------------------------
# Supabase (production)
# --------------------------------------------------------------------------------------
class SupabaseStore:
    name = "supabase"

    def __init__(self, url: str, service_key: str, anon_key: str):
        from supabase import create_client

        self._url = url
        self._anon_key = anon_key
        # Service-role client: server-side only, used for database tables. Never use it for
        # sign-in (it would keep a user session on a client shared by every visitor).
        self._db = create_client(url, service_key)

    def _auth_client(self):
        from supabase import create_client

        return create_client(self._url, self._anon_key)  # fresh client per auth action

    # ---- auth (email + password) ----
    def sign_up(self, email: str, password: str, name: str, phone: str) -> str:
        try:
            res = self._auth_client().auth.sign_up(
                {"email": email, "password": password,
                 "options": {"data": {"full_name": name, "phone": phone}}}
            )
        except Exception as exc:
            raise StoreError(_friendly_auth_error(exc)) from exc
        self.upsert_profile(email, name=name, phone=phone, provider="email", touch_login=False)
        if res.session is None:
            return "confirm"   # Supabase sent a confirmation email
        return "ok"

    def sign_in(self, email: str, password: str) -> dict:
        try:
            res = self._auth_client().auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            raise StoreError(_friendly_auth_error(exc)) from exc
        meta = (res.user.user_metadata or {}) if res.user else {}
        return {"email": email, "name": meta.get("full_name") or email.split("@")[0], "provider": "email"}

    def reset_password(self, email: str) -> None:
        try:
            self._auth_client().auth.reset_password_for_email(email)
        except Exception as exc:
            raise StoreError(_friendly_auth_error(exc)) from exc

    # ---- profiles ----
    def get_profile(self, email: str) -> dict | None:
        res = self._db.table("profiles").select("*").eq("email", email).limit(1).execute()
        return res.data[0] if res.data else None

    def upsert_profile(self, email: str, name: str | None = None, phone: str | None = None,
                       provider: str | None = None, touch_login: bool = True) -> dict:
        existing = self.get_profile(email)
        row: dict = {"email": email}
        if existing is None:
            row.update({"name": name or email.split("@")[0], "phone": phone or "",
                        "provider": provider or "email", "plan": "free"})
        else:
            if name and not existing.get("name"):
                row["name"] = name
            if phone and not existing.get("phone"):
                row["phone"] = phone
        if touch_login:
            row["last_login_at"] = _iso(now_utc())
        res = self._db.table("profiles").upsert(row, on_conflict="email").execute()
        return res.data[0] if res.data else (self.get_profile(email) or row)

    def update_profile(self, email: str, **fields) -> None:
        self._db.table("profiles").update(fields).eq("email", email).execute()

    def list_profiles(self) -> list[dict]:
        return self._db.table("profiles").select("*").order("created_at", desc=True).execute().data or []

    # ---- usage ----
    def add_usage(self, email: str, files_count: int, pdf_count: int, bytes_before: int, bytes_after: int) -> None:
        self._db.table("usage_events").insert({
            "email": email, "files_count": files_count, "pdf_count": pdf_count,
            "bytes_before": bytes_before, "bytes_after": bytes_after,
        }).execute()

    def usage_since(self, email: str, since: datetime) -> tuple[int, int]:
        res = (self._db.table("usage_events").select("files_count,pdf_count")
               .eq("email", email).gte("created_at", _iso(since)).execute())
        rows = res.data or []
        return sum(r["files_count"] or 0 for r in rows), sum(r["pdf_count"] or 0 for r in rows)

    def usage_rows_since(self, since: datetime) -> list[dict]:
        res = (self._db.table("usage_events").select("email,files_count,pdf_count,bytes_before,bytes_after,created_at")
               .gte("created_at", _iso(since)).execute())
        return res.data or []

    def reset_usage(self, email: str) -> None:
        self._db.table("usage_events").delete().eq("email", email).execute()

    def reset_all_usage(self) -> None:
        # PostgREST needs a filter on delete; id >= 0 matches every row
        self._db.table("usage_events").delete().gte("id", 0).execute()

    def delete_user_data(self, email: str) -> None:
        self._db.table("upgrade_requests").delete().eq("email", email).execute()
        self._db.table("usage_events").delete().eq("email", email).execute()
        self._db.table("profiles").delete().eq("email", email).execute()

    # ---- plans ----
    def set_plan(self, email: str, plan_id: str, days: int = PLAN_DAYS) -> None:
        if plan_id == "free":
            fields = {"plan": "free", "plan_started_at": None, "plan_expires_at": None}
        else:
            start = now_utc()
            fields = {"plan": plan_id, "plan_started_at": _iso(start),
                      "plan_expires_at": _iso(start + timedelta(days=days))}
        self.update_profile(email, **fields)

    # ---- upgrade requests ----
    def create_upgrade_request(self, email: str, plan_id: str, note: str = "") -> None:
        self._db.table("upgrade_requests").insert({"email": email, "plan": plan_id, "note": note}).execute()

    def list_upgrade_requests(self, status: str | None = "pending", email: str | None = None) -> list[dict]:
        q = self._db.table("upgrade_requests").select("*").order("created_at", desc=True)
        if status:
            q = q.eq("status", status)
        if email:
            q = q.eq("email", email)
        return q.execute().data or []

    def set_request_status(self, request_id: int, status: str) -> None:
        self._db.table("upgrade_requests").update({"status": status}).eq("id", request_id).execute()

    # ---- orders / payments (stored in upgrade_requests) ----
    def create_order(self, email: str, plan_id: str, amount_inr: int, method: str, order_ref: str,
                     gateway_ref: str = "", qr_url: str = "") -> dict:
        res = self._db.table("upgrade_requests").insert({
            "email": email, "plan": plan_id, "amount_inr": amount_inr, "method": method,
            "order_ref": order_ref, "gateway_ref": gateway_ref, "qr_url": qr_url, "status": "pending",
        }).execute()
        return res.data[0]

    def get_order(self, order_id: int) -> dict | None:
        res = self._db.table("upgrade_requests").select("*").eq("id", order_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_order(self, order_id: int, **fields) -> None:
        self._db.table("upgrade_requests").update(fields).eq("id", order_id).execute()

    # ---- app settings (admin-editable plans etc.) ----
    def get_setting(self, key: str):
        res = self._db.table("app_settings").select("value").eq("key", key).limit(1).execute()
        return res.data[0]["value"] if res.data else None

    def set_setting(self, key: str, value) -> None:
        self._db.table("app_settings").upsert(
            {"key": key, "value": value, "updated_at": _iso(now_utc())}, on_conflict="key").execute()

    def list_orders(self, statuses: list[str] | None = None, email: str | None = None, limit: int = 200) -> list[dict]:
        q = self._db.table("upgrade_requests").select("*").order("created_at", desc=True).limit(limit)
        if statuses:
            q = q.in_("status", statuses)
        if email:
            q = q.eq("email", email)
        return q.execute().data or []


def _friendly_auth_error(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "invalid login credentials" in low:
        return "Wrong email or password."
    if "email not confirmed" in low:
        return "Please confirm your email first - check your inbox for the confirmation link."
    if "already registered" in low or "already been registered" in low:
        return "An account with this email already exists. Try logging in."
    if "password" in low and ("6" in low or "short" in low or "weak" in low):
        return "Password is too weak. Use at least 8 characters."
    if "rate limit" in low:
        return "Too many attempts. Please wait a minute and try again."
    return f"Could not complete that: {msg[:140]}"


# --------------------------------------------------------------------------------------
# SQLite (local demo / testing only)
# --------------------------------------------------------------------------------------
_SCHEMA = """
create table if not exists auth_users (email text primary key, pw_hash text not null, salt text not null);
create table if not exists profiles (
    email text primary key, name text, phone text, provider text, plan text default 'free',
    plan_started_at text, plan_expires_at text,
    created_at text default (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')), last_login_at text);
create table if not exists usage_events (
    id integer primary key autoincrement, email text, files_count integer, pdf_count integer,
    bytes_before integer, bytes_after integer,
    created_at text default (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')));
create table if not exists app_settings (key text primary key, value text, updated_at text);
create table if not exists upgrade_requests (
    id integer primary key autoincrement, email text, plan text, note text, status text default 'pending',
    amount_inr integer default 0, method text default 'manual', order_ref text default '', utr text default '',
    gateway_ref text default '', qr_url text default '', paid_at text,
    created_at text default (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')));
"""


class LocalStore:
    name = "local"

    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        for col in ("amount_inr integer default 0", "method text default 'manual'", "order_ref text default ''",
                    "utr text default ''", "gateway_ref text default ''", "qr_url text default ''", "paid_at text"):
            try:  # upgrade an older demo database
                self._conn.execute(f"alter table upgrade_requests add column {col}")
            except sqlite3.OperationalError:
                pass
        self._conn.commit()

    def _q(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, args)
            rows = [dict(r) for r in cur.fetchall()]
            self._conn.commit()
            return rows

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()

    def sign_up(self, email: str, password: str, name: str, phone: str) -> str:
        if self._q("select 1 from auth_users where email=?", (email,)):
            raise StoreError("An account with this email already exists. Try logging in.")
        salt = pysecrets.token_hex(16)
        self._q("insert into auth_users(email,pw_hash,salt) values (?,?,?)", (email, self._hash(password, salt), salt))
        self.upsert_profile(email, name=name, phone=phone, provider="email", touch_login=False)
        return "ok"

    def sign_in(self, email: str, password: str) -> dict:
        rows = self._q("select * from auth_users where email=?", (email,))
        if not rows or not hmac.compare_digest(rows[0]["pw_hash"], self._hash(password, rows[0]["salt"])):
            raise StoreError("Wrong email or password.")
        prof = self.get_profile(email) or {}
        return {"email": email, "name": prof.get("name") or email.split("@")[0], "provider": "email"}

    def reset_password(self, email: str) -> None:
        raise StoreError("Password reset emails work only with Supabase (not in local demo mode).")

    def get_profile(self, email: str) -> dict | None:
        rows = self._q("select * from profiles where email=?", (email,))
        return rows[0] if rows else None

    def upsert_profile(self, email: str, name: str | None = None, phone: str | None = None,
                       provider: str | None = None, touch_login: bool = True) -> dict:
        existing = self.get_profile(email)
        if existing is None:
            self._q("insert into profiles(email,name,phone,provider,plan) values (?,?,?,?, 'free')",
                    (email, name or email.split("@")[0], phone or "", provider or "email"))
        else:
            if name and not existing.get("name"):
                self._q("update profiles set name=? where email=?", (name, email))
            if phone and not existing.get("phone"):
                self._q("update profiles set phone=? where email=?", (phone, email))
        if touch_login:
            self._q("update profiles set last_login_at=? where email=?", (_iso(now_utc()), email))
        return self.get_profile(email)

    def update_profile(self, email: str, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self._q(f"update profiles set {cols} where email=?", (*fields.values(), email))

    def list_profiles(self) -> list[dict]:
        return self._q("select * from profiles order by created_at desc")

    def add_usage(self, email, files_count, pdf_count, bytes_before, bytes_after) -> None:
        self._q("insert into usage_events(email,files_count,pdf_count,bytes_before,bytes_after) values (?,?,?,?,?)",
                (email, files_count, pdf_count, bytes_before, bytes_after))

    def usage_since(self, email: str, since: datetime) -> tuple[int, int]:
        rows = self._q("select coalesce(sum(files_count),0) f, coalesce(sum(pdf_count),0) p from usage_events "
                       "where email=? and created_at >= ?", (email, _iso(since)))
        return int(rows[0]["f"]), int(rows[0]["p"])

    def usage_rows_since(self, since: datetime) -> list[dict]:
        return self._q("select email,files_count,pdf_count,bytes_before,bytes_after,created_at from usage_events "
                       "where created_at >= ?", (_iso(since),))

    def reset_usage(self, email: str) -> None:
        self._q("delete from usage_events where email=?", (email,))

    def reset_all_usage(self) -> None:
        self._q("delete from usage_events")

    def delete_user_data(self, email: str) -> None:
        for t in ("upgrade_requests", "usage_events", "profiles", "auth_users"):
            self._q(f"delete from {t} where email=?", (email,))

    def set_plan(self, email: str, plan_id: str, days: int = PLAN_DAYS) -> None:
        if plan_id == "free":
            self.update_profile(email, plan="free", plan_started_at=None, plan_expires_at=None)
        else:
            start = now_utc()
            self.update_profile(email, plan=plan_id, plan_started_at=_iso(start),
                                plan_expires_at=_iso(start + timedelta(days=days)))

    def create_upgrade_request(self, email: str, plan_id: str, note: str = "") -> None:
        self._q("insert into upgrade_requests(email,plan,note) values (?,?,?)", (email, plan_id, note))

    def list_upgrade_requests(self, status: str | None = "pending", email: str | None = None) -> list[dict]:
        sql, args = "select * from upgrade_requests where 1=1", []
        if status:
            sql += " and status=?"; args.append(status)
        if email:
            sql += " and email=?"; args.append(email)
        return self._q(sql + " order by created_at desc", tuple(args))

    def set_request_status(self, request_id: int, status: str) -> None:
        self._q("update upgrade_requests set status=? where id=?", (status, request_id))

    def create_order(self, email, plan_id, amount_inr, method, order_ref, gateway_ref="", qr_url="") -> dict:
        with self._lock:
            cur = self._conn.execute(
                "insert into upgrade_requests(email,plan,amount_inr,method,order_ref,gateway_ref,qr_url,status) "
                "values (?,?,?,?,?,?,?, 'pending')", (email, plan_id, amount_inr, method, order_ref, gateway_ref, qr_url))
            self._conn.commit()
            new_id = cur.lastrowid
        return self.get_order(new_id)

    def get_order(self, order_id: int) -> dict | None:
        rows = self._q("select * from upgrade_requests where id=?", (order_id,))
        return rows[0] if rows else None

    def update_order(self, order_id: int, **fields) -> None:
        if fields:
            cols = ", ".join(f"{k}=?" for k in fields)
            self._q(f"update upgrade_requests set {cols} where id=?", (*fields.values(), order_id))

    def get_setting(self, key: str):
        import json
        rows = self._q("select value from app_settings where key=?", (key,))
        return json.loads(rows[0]["value"]) if rows and rows[0]["value"] else None

    def set_setting(self, key: str, value) -> None:
        import json
        self._q("insert into app_settings(key,value,updated_at) values (?,?,?) "
                "on conflict(key) do update set value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value), _iso(now_utc())))

    def list_orders(self, statuses=None, email=None, limit: int = 200) -> list[dict]:
        sql, args = "select * from upgrade_requests where 1=1", []
        if statuses:
            sql += " and status in (%s)" % ",".join("?" * len(statuses)); args += list(statuses)
        if email:
            sql += " and email=?"; args.append(email)
        return self._q(sql + " order by created_at desc limit ?", (*args, limit))


# --------------------------------------------------------------------------------------
# Changes whenever this file changes, so an updated app never keeps an old store object in memory
# (Streamlit Cloud reloads code on a GitHub push without restarting, but cached objects would survive).
_CODE_VERSION = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]


@st.cache_resource(show_spinner=False)
def _make_store(kind: str, url: str = "", service_key: str = "", anon_key: str = "", version: str = ""):
    if kind == "supabase":
        return SupabaseStore(url, service_key, anon_key)
    path = os.environ.get("SPC_DEMO_DB", str(Path(__file__).resolve().parent.parent / "demo_data.sqlite3"))
    return LocalStore(path)


def get_store():
    """The active store, or None if nothing is configured yet."""
    if config.supabase_configured():
        return _make_store("supabase", config.setting("supabase", "url"),
                           config.setting("supabase", "service_key"), config.setting("supabase", "anon_key"),
                           version=_CODE_VERSION)
    if config.demo_mode():
        return _make_store("local", version=_CODE_VERSION)
    return None
