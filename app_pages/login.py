"""Login / Sign up page: Google (one click) or email + password."""
import re

import streamlit as st

from core import config, nav
from core.auth import current_user, login_email, signup_email
from core.store import StoreError, get_store
from core.ui import raw_html

if current_user():
    st.switch_page(nav.page("checkout" if st.session_state.get("checkout_plan") else "compressor"))

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_, mid, _ = st.columns([1, 1.25, 1])
with mid:
    with st.container(key="glasscard_auth"):
        raw_html('<div class="auth-hero"><h2>Welcome</h2>'
                 '<p>Log in or create a free account. 5 free uploads every day, no card needed.</p></div>')

        if config.google_configured():
            if st.button("Continue with Google", key="google_login", use_container_width=True):
                st.login("google")
        else:
            st.button("Continue with Google", key="google_login", use_container_width=True, disabled=True,
                      help="Add Google OAuth keys in Secrets to enable this (see README).")

        st.caption("By continuing you agree to the [Terms](/terms) and [Privacy Policy](/privacy).")

        raw_html('<div class="or-divider">or use email</div>')

        store_ready = get_store() is not None
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("login_form", border=False):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary", use_container_width=True,
                                                  disabled=not store_ready)
            if submitted:
                if not EMAIL_RE.match(email.strip()) or not password:
                    st.error("Enter a valid email and your password.")
                else:
                    try:
                        login_email(email, password)
                        st.switch_page(nav.page("checkout" if st.session_state.get("checkout_plan") else "compressor"))
                    except StoreError as exc:
                        st.error(str(exc))

            with st.expander("Forgot password?"):
                reset_email = st.text_input("Your account email", key="reset_email")
                if st.button("Send reset link", key="reset_btn", disabled=not store_ready):
                    try:
                        get_store().reset_password(reset_email.strip().lower())
                        st.success("If that email has an account, a reset link is on its way.")
                    except StoreError as exc:
                        st.error(str(exc))

        with tab_signup:
            with st.form("signup_form", border=False):
                name = st.text_input("Full name")
                s_email = st.text_input("Email ", placeholder="you@example.com")
                phone = st.text_input("Phone (optional)", placeholder="+91 98765 43210")
                s_pw = st.text_input("Password", type="password", help="At least 8 characters.", key="s_pw")
                s_pw2 = st.text_input("Confirm password", type="password", key="s_pw2")
                agree = st.checkbox("I agree to the [Terms](/terms) and [Privacy Policy](/privacy).")
                created = st.form_submit_button("Create free account", type="primary", use_container_width=True,
                                                disabled=not store_ready)
            if created:
                errors = []
                if len(name.strip()) < 2:
                    errors.append("Enter your full name.")
                if not EMAIL_RE.match(s_email.strip()):
                    errors.append("Enter a valid email address.")
                if len(s_pw) < 8:
                    errors.append("Password must be at least 8 characters.")
                if s_pw != s_pw2:
                    errors.append("Passwords do not match.")
                if not agree:
                    errors.append("Please accept the Terms and Privacy Policy.")
                if errors:
                    st.error(" ".join(errors))
                else:
                    try:
                        result = signup_email(name, s_email, phone, s_pw)
                        if result == "confirm":
                            st.success("Account created! Check your inbox and click the confirmation link, then log in.")
                        else:
                            st.switch_page(nav.page("checkout" if st.session_state.get("checkout_plan") else "compressor"))
                    except StoreError as exc:
                        st.error(str(exc))

    if not get_store():
        st.info("Login is not configured yet. The site owner needs to add Supabase keys (see README).")
    st.page_link(nav.page("pricing"), label="See plans & pricing", icon=":material/workspace_premium:",
                 use_container_width=True)
