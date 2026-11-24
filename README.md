# Smart PDF Compressor

Compress PDFs and ZIP archives of PDFs in seconds, with a glass UI, live logs,
Google / email login, and Free + Pro plans.

- **Free**: 5 ZIP/PDF uploads per day (max 100 PDFs/day), resets at midnight IST
- **Pro 1K**: $50/month, 1,000 PDFs · **Pro 3K**: $70/month, 3,000 PDFs · **Unlimited**: $150/month

Files are processed in a temporary folder and deleted right after compression.
The database only stores accounts, plans and usage counts, never the PDFs.

---

## Project layout

```
streamlit_app.py          entry point: theme, header, navigation
app_pages/
  compressor.py           the compression tool + plan limits
  login.py                Google login, email sign up / log in
  pricing.py              Free vs Pro cards (USD + INR)
  account.py              user profile, plan, usage
  admin.py                admin: users, upgrade requests, plans, reset/delete
core/
  plans.py                plans, prices and limits  <- change pricing here
  store.py                database (Supabase; SQLite for local demo)
  auth.py                 who is logged in
  theme.py                glass theme
supabase_schema.sql       run once in Supabase
requirements.txt          Python packages
packages.txt              Ghostscript + qpdf (installed by Streamlit Cloud)
.streamlit/config.toml    theme + toolbar settings
.streamlit/secrets.toml.example   template for your secrets
```

---

## 1. Try it locally (no setup)

```bash
pip install -r requirements.txt          # also install Ghostscript on your PC
SPC_DEMO=1 SPC_APP_ADMIN_EMAILS=you@example.com streamlit run streamlit_app.py
```
Windows PowerShell:
```powershell
$env:SPC_DEMO="1"; $env:SPC_APP_ADMIN_EMAILS="you@example.com"; streamlit run streamlit_app.py
```
Demo mode stores data in `demo_data.sqlite3` and disables Google login. Sign up with the
admin email to see the **Admin** page.

---

## 2. Supabase (database + email login), free

1. Create a project at **supabase.com**.
2. **SQL Editor → New query** → paste `supabase_schema.sql` → **Run**.
3. **Project Settings → API keys**: copy the **Project URL**, the **anon / publishable** key
   and the **service_role / secret** key.
4. **Authentication → URL Configuration**: set **Site URL** to your app URL
   (e.g. `https://smart-pdf-compressor.streamlit.app`) so confirmation and reset emails link back to it.
5. Optional: **Authentication → Providers → Email**: turn off "Confirm email" if you want
   users to log in right after signing up.

Free Supabase projects pause after a week with no activity. If that happens, open the
dashboard and click **Restore**.

## 3. Google login, free

1. Go to **console.cloud.google.com** → create a project.
2. Set up the **OAuth consent screen** (External, app name, support email).
3. Create an **OAuth client ID** of type **Web application** and add these
   **Authorized redirect URIs**:
   - `https://YOUR-APP.streamlit.app/oauth2callback`
   - `http://localhost:8501/oauth2callback` (for local testing)
4. Copy the **Client ID** and **Client secret**.

## 4. Deploy on Streamlit Community Cloud, free

1. Push this folder to a **public GitHub repo** (`.streamlit/secrets.toml` is git-ignored, keep it that way).
2. **share.streamlit.io → Create app** → pick the repo, main file `streamlit_app.py`,
   **Advanced settings → Python 3.12**.
3. In **Secrets**, paste `.streamlit/secrets.toml.example` filled with your real values.
4. Deploy. Sign in with the email listed in `admin_emails` to get the Admin page.

---

## Managing users

- **Admin page** (in the app): all users, today's and 30-day usage, pending upgrade requests.
  - **Activate**: gives the requested Pro plan for 30 days.
  - **Change plan**: any plan, any number of days.
  - **Reset usage**: clears a user's usage, so their limit starts from zero again.
  - **Delete user data**: removes profile, usage and requests.
- **Supabase dashboard**: Table Editor (`profiles`, `usage_events`, `upgrade_requests`) and
  Authentication → Users for email/password accounts.

## Payments (UPI)

Prices in INR are fixed in `core/plans.py` (`price_inr`): Pro 1K ₹4,799 · Pro 3K ₹6,699 · Unlimited ₹14,399.
"Get Pro" opens a checkout page with a UPI QR for the exact amount. Two modes:

**1. Direct UPI (free, works today).** Add your UPI ID in Secrets:
```toml
[payments]
upi_id = "yourname@okaxis"
payee_name = "Smart PDF Compressor"
```
The user scans the QR, pays, and enters the 12-digit UTR. The payment shows up in
**Admin → Payments to verify**. Check it in your bank/UPI app and click **Activate**.

**2. Razorpay (fully automatic).** Add your Razorpay API keys:
```toml
[razorpay]
key_id = "rzp_live_..."
key_secret = "..."
```
Each order gets a single-use Razorpay UPI QR (valid 30 minutes). The checkout page checks it
every 5 seconds and activates the plan as soon as the payment is captured. A payment made after
the user closed the tab is picked up the next time they open Pricing or Account.
Razorpay's UPI QR feature must be enabled for your account (ask Razorpay support).

Existing installs: run `supabase_payments_update.sql` once in the Supabase SQL Editor.

## Notes

- Email/password sessions last until the browser tab is reloaded; Google login stays
  signed in (cookie).
- Change prices or limits in `core/plans.py`. INR prices use a live USD→INR rate
  (fallback ₹96 if the rate service is unreachable).
- `allow_folder_export` must stay `false` on the public site (it would write to the server's disk).
