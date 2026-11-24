"""Admin -> Plans: edit every plan (name, prices, limits, days, features, visibility) without code."""
import streamlit as st

from core import nav
from core.auth import current_user, invalidate_profile, is_admin
from core.plan_settings import save_plans
from core.plans import DEFAULT_PLANS, PLANS, plan_to_dict
from core.store import get_store

user = current_user()
if not user:
    st.switch_page(nav.page("login"))
if not is_admin(user):
    st.error("This page is only for the site admin.")
    st.stop()
if get_store() is None:
    st.error("Database is not configured.")
    st.stop()

st.subheader("Plans & pricing")
st.caption("Changes apply everywhere right after you click Save: pricing page, checkout QR amount and every "
           "user's limits. Unpaid orders at an old price are cancelled automatically. New 'days valid' "
           "applies to new purchases.")


def current_settings() -> dict:
    return {pid: plan_to_dict(p) for pid, p in PLANS.items()}


def limit_inputs(label: str, value, key: str, help_text: str):
    unlimited = st.checkbox(f"Unlimited {label.lower()}", value=value is None, key=f"{key}_unl")
    number = st.number_input(label, min_value=0, max_value=10_000_000, step=1,
                             value=int(value) if value is not None else 100, key=key, help=help_text)
    return None if unlimited else int(number)


plan_ids = list(PLANS)
for row_start in range(0, len(plan_ids), 2):
    cols = st.columns(2, gap="large")
    for col, pid in zip(cols, plan_ids[row_start:row_start + 2]):
        plan = PLANS[pid]
        is_free = pid == "free"
        with col, st.container(key=f"glasscard_plan_{pid}"):
            st.markdown(f"**{plan.name}**  ·  `{pid}`" + ("  ·  free plan (limits reset daily)" if is_free else ""))
            with st.form(f"plan_form_{pid}", border=False):
                c1, c2 = st.columns(2)
                name = c1.text_input("Name", value=plan.name, max_chars=40, key=f"{pid}_name")
                tagline = c2.text_input("Tagline", value=plan.tagline, max_chars=40, key=f"{pid}_tag")
                if not is_free:
                    p1, p2, p3 = st.columns(3)
                    price_inr = p1.number_input("Price ₹ (UPI)", min_value=1, max_value=10_000_000, step=1,
                                                value=max(1, plan.price_inr), key=f"{pid}_inr")
                    price_usd = p2.number_input("Price $ (shown)", min_value=0, max_value=1_000_000, step=1,
                                                value=plan.price_usd, key=f"{pid}_usd")
                    days = p3.number_input("Days valid", min_value=1, max_value=3650, step=1,
                                           value=plan.days, key=f"{pid}_days")
                l1, l2 = st.columns(2)
                with l1:
                    pdf_limit = limit_inputs("PDFs limit", plan.pdf_limit, f"{pid}_pdf",
                                             "PDFs per day (Free) or per plan period (Pro).")
                with l2:
                    file_limit = limit_inputs("Uploads limit", plan.file_limit, f"{pid}_files",
                                              "ZIP/PDF files a user can select per day (Free) or per plan period (Pro).")
                extras = st.text_area("Extra feature lines (one per line)", value="\n".join(plan.extras),
                                      height=90, key=f"{pid}_extras",
                                      help="Limit lines are added automatically from the numbers above.")
                if not is_free:
                    v1, v2 = st.columns(2)
                    visible = v1.checkbox("Show on pricing page", value=plan.visible, key=f"{pid}_vis")
                    popular = v2.checkbox("Mark as 'Most popular'", value=plan.popular, key=f"{pid}_pop")
                saved = st.form_submit_button(f"Save {plan.name}", type="primary", use_container_width=True)

            if saved:
                settings = current_settings()
                new = {"name": name, "tagline": tagline, "pdf_limit": pdf_limit, "file_limit": file_limit,
                       "extras": [x for x in extras.splitlines() if x.strip()]}
                if not is_free:
                    new.update(price_inr=int(price_inr), price_usd=int(price_usd), days=int(days),
                               visible=bool(visible), popular=bool(popular))
                    if popular:  # only one "Most popular"
                        for other in settings:
                            settings[other]["popular"] = False
                settings[pid].update(new)
                try:
                    save_plans(settings)
                    invalidate_profile()
                    st.toast(f"{name} saved")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save: {exc}. Did you run supabase_plans_update.sql?")

            st.caption("Shown on pricing: " + " · ".join(plan.features))

st.divider()
r1, r2 = st.columns([3, 1.2], vertical_alignment="center")
with r1:
    sure = st.checkbox("Reset all plans to the original default values", key="plans_reset_sure")
with r2:
    if st.button("Reset to defaults", disabled=not sure, use_container_width=True):
        save_plans({})
        invalidate_profile()
        st.toast("All plans reset to defaults")
        st.rerun()
st.page_link(nav.page("pricing"), label="Open the pricing page to see the result", icon=":material/visibility:")
st.caption("Defaults: " + ", ".join(f"{p.name} ₹{p.price_inr:,}" for p in DEFAULT_PLANS.values() if p.id != "free"))
