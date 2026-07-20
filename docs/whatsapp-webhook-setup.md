# WhatsApp Webhook & Access Token Setup

How to configure the WhatsApp Cloud API webhook in the Meta dashboard and where
the two different tokens come from.

## Webhook configuration (Meta App Dashboard → WhatsApp → Configuration)

| Field | Value |
|-------|-------|
| **Callback URL** | `https://app.cocoontimor.org/webhooks/whatsapp/` |
| **Verify token** | `MvaVYTZUC3_wG_lCMhukZwzx8qN-9ufUnFd29yTMy7k` |

Notes:
- **Keep the trailing slash** on the Callback URL. The Django route is defined
  with one; without it Django 301-redirects and Meta's verification GET may not
  follow the redirect, causing verification to fail.
- **"Verify and save" only works after the app is live** with valid HTTPS —
  Meta hits the Callback URL immediately. Do this step after the full apply +
  DNS + Let's Encrypt TLS are in place.
- Per the dashboard banner, **production message delivery also requires the app
  to be published**.

### How the path resolves
- `src/cocoon/urls.py` → `path("webhooks/whatsapp/", include("messaging.webhook_urls"))`
- `src/messaging/webhook_urls.py` → `path("", whatsapp_webhook)`
- View: `src/messaging/views.py::whatsapp_webhook`
  - **GET** = verification: requires `hub.mode == "subscribe"` and
    `hub.verify_token == WHATSAPP_WEBHOOK_VERIFY_TOKEN`, then echoes `hub.challenge`.
  - **POST** = events (`@csrf_exempt`, unauthenticated): delivery statuses + inbound messages.

## The two tokens (different sources)

### 1. Verify token — you generate it
An arbitrary shared string; **not** a Meta credential. It is non-secret and
lives in `infra/terraform.tfvars` (`whatsapp_webhook_verify_token`), flows to the
VM's `app.env` → `settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN`. Paste the same value
into the Meta dashboard's Verify token field.

Regenerate with:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
If you change it, update `terraform.tfvars` and re-apply, then update the dashboard.

### 2. Access token — issued by Meta (cannot be self-generated)
Authenticates outbound WhatsApp API calls. Stored in **GCP Secret Manager**
(`whatsapp-access-token-prod`), never committed.

**Temporary (24h, testing only):**
Meta App Dashboard → your app → **WhatsApp → API Setup** → copy the
**Temporary access token**. Expires daily — not for prod.

**Permanent (prod) — via a System User:**
1. business.facebook.com → **Business Settings → Users → System users**
2. Create a system user (role: Admin or Employee).
3. **Add assets** → assign your WhatsApp app / WABA with full control.
4. **Generate new token** → select the app → scopes
   `whatsapp_business_messaging` + `whatsapp_business_management`.
5. Set expiry **Never**, generate, copy (shown only once).

Store it:
```bash
printf 'PASTE_THE_ACCESS_TOKEN' | \
  gcloud secrets versions add whatsapp-access-token-prod --data-file=- \
  --project=decent-genius-503000-h2 --account=support@cocoontimor.org
```

> ⚠️ The token currently in `app-backend/.env` is exposed. **Revoke it** in the
> Meta dashboard and use a fresh permanent token for prod.

## Related: populate the other prod secrets
```bash
# Django SECRET_KEY (generate + store directly)
python3 -c 'import secrets; print(secrets.token_urlsafe(64))' | \
  gcloud secrets versions add django-secret-key-prod --data-file=- \
  --project=decent-genius-503000-h2 --account=support@cocoontimor.org

# Postgres password for user coccon_db_admin
printf 'THE_DB_PASSWORD' | \
  gcloud secrets versions add postgres-password-prod --data-file=- \
  --project=decent-genius-503000-h2 --account=support@cocoontimor.org
```

`WHATSAPP_PHONE_NUMBER_ID` (`1138871972650860`) is non-secret and set in
`terraform.tfvars`.
