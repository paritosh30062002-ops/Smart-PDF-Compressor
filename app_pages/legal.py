"""Terms, Privacy and Refund pages (text only, public: no login needed)."""
import streamlit as st

from core import config

LAST_UPDATED = "24 November 2026"
REFUND_DAYS = 7           # days after payment in which a refund can be requested
REFUND_PROCESS_DAYS = 7   # working days to send an approved refund


def _contact() -> str:
    return config.support_contact() or "the site owner"


def _business() -> str:
    return str(config.setting("app", "business_name", "") or "Smart PDF Compressor")


def _show(title: str, body: str) -> None:
    with st.container(key="glasscard_legal"):
        st.header(title, anchor=False)
        st.caption(f"Last updated: {LAST_UPDATED}")
        st.markdown(body)


def terms() -> None:
    _show("Terms of Service", f"""
These terms apply when you use {_business()} ("we", "us"). By creating an account, logging in or paying for a plan, you agree to them.

#### 1. The service
We compress PDF files, and PDFs inside ZIP archives. Results depend on the file: some PDFs become much smaller, some are already optimal and are returned unchanged. Compression can lower image quality, so keep your original files until you have checked the result.

#### 2. Your account
Give correct details, keep your password private and use your own account only. You are responsible for activity on your account.

#### 3. Fair use
- Upload only files you own or have permission to process.
- Do not upload malware or illegal content, or try to break, overload or bypass the limits of the service.
- Do not resell access or share one account between several people to avoid plan limits.

We may suspend accounts that break these rules.

#### 4. Plans and payments
- Plan limits, prices and validity are shown on the Pricing page. Prices are charged in INR; USD prices are for reference.
- Payments are made by UPI. After paying, submit the correct UTR / transaction ID for your own payment. Each UTR can be used once.
- Paid plans are activated after we verify the payment, and do not renew automatically.
- If you pay again while the same plan is active, a new plan period starts on the day of activation.
- When a plan ends, your account returns to the Free plan.
- Submitting a false UTR, or one for another person's payment, can lead to suspension.

Refunds are covered by the Refund Policy.

#### 5. Your files
Your files remain yours. We use them only to compress them for you, as explained in the Privacy Policy.

#### 6. Availability and liability
The service is provided "as is", and we cannot promise it will always be available or error-free. To the extent allowed by law, our total liability for a claim is limited to the amount you paid for your current plan period. Nothing here removes rights you have under applicable consumer law.

#### 7. Changes and law
We may update these terms; the date above shows the latest version. These terms are governed by the laws of India.

#### 8. Contact
Questions or complaints: {_contact()}.
""")


def privacy() -> None:
    _show("Privacy Policy", f"""
This policy explains what {_business()} collects and why.

#### What we collect
- **Account:** your name, email, optional phone number, login method and last login time. If you use Google, we receive your name and email from Google, not your password.
- **Password:** for email accounts, passwords are handled by our login provider, Supabase. We do not store them in our own tables.
- **Usage:** number of files and PDFs compressed, sizes before and after, and time.
- **Payments:** plan, amount, order number, UTR, status and dates. We do not collect your UPI PIN, card or bank login details.

#### Your files
- Files are uploaded to our server over the internet and are not saved to our database.
- Working copies are kept in a temporary folder that is deleted after compression.
- The upload and the compressed result stay in server memory so you can download the result, and are cleared after your session ends.
- We do not sell your files or use them for advertising.

#### Why we use this data
To log you in, apply plan limits, verify payments, provide receipts, give support, prevent misuse and meet legal duties.

#### Who processes it
- **Supabase:** accounts and database.
- **Google:** only if you choose Google login.
- **Our hosting provider:** runs the app, and may keep technical logs and usage statistics.

Payments happen in your own UPI app. These providers may process data outside your country. We do not sell your personal data.

#### Cookies
We use cookies and similar browser storage needed for login and for the app to work. Our hosting provider may set its own.

#### How long we keep it
Account and usage data is kept while your account exists. Payment records may be kept longer where needed for tax, accounting or disputes.

#### Your choices
You can ask for a copy, correction or deletion of your data, withdraw consent, or raise a grievance by contacting {_contact()}. We may need to confirm your identity first. Some data, such as payment records, may have to be kept by law.

#### Children
The service is meant for people aged 18 or over.

#### Security and changes
Database access is restricted to our server. No online service is perfectly secure. We may update this policy; the date above shows the latest version.
""")


def refund() -> None:
    _show("Refund Policy", f"""
#### When you can get a refund
- You were charged twice for the same order.
- You paid, but your plan was not activated and we could not fix it.
- A fault on our side stopped you from using your paid plan, and we could not fix it.
- You paid the wrong amount and we could not activate the plan.

#### When a refund is normally not given
- You changed your mind after the plan was activated.
- You used only part of the plan, or the plan period ended.
- A file could not be reduced because it was already optimal, encrypted or damaged.
- Your account was suspended for breaking the Terms of Service.

Try the Free plan first to see whether the results suit you. Nothing here removes rights you have under applicable consumer law.

#### How to ask
Contact {_contact()} within **{REFUND_DAYS} days** of payment, with your account email, order number and UTR.

#### Processing
Approved refunds are sent to the original payment source within **{REFUND_PROCESS_DAYS} working days** of approval. Your bank may take extra time. The paid plan ends when it is refunded.

#### Cancelling
An unpaid order can be cancelled on the checkout page. Plans do not renew automatically, so there is nothing to cancel after a plan ends.
""")
