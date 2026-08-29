# WhatsApp Phone Number Registration Runbook

How to register (activate) a WhatsApp Cloud API phone number so it can send and
receive messages via `graph.facebook.com`. Based on
<https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/registration>.

## What "registration" does

Activates a number on the Cloud API. Prerequisites (done earlier in WhatsApp
Manager, **not** part of this call):
1. Number added to the WhatsApp Business Account (WABA).
2. Ownership verified via SMS/voice code.
3. A Phone Number ID issued for the number.
4. A valid access token with `whatsapp_business_management` +
   `whatsapp_business_messaging`.

## The call

`POST https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/register`

| Parameter | Value |
|-----------|-------|
| `messaging_product` | `whatsapp` (required) |
| `pin` | 6-digit two-step verification PIN (required) |
| `data_localization_region` | optional 2-letter ISO region (e.g. `IN`, `DE`) |

### About the PIN
- The number's **two-step verification PIN**. Unrelated to the ownership SMS code.
- Fresh number with no PIN → the value you pass **becomes** the PIN.
- Number already has two-step verification → you must pass the **existing** PIN.
- **Rate limit:** max 10 register attempts per number / 72h. Exceeding →
  error `133016`, blocked for 72h. Do **not** brute-force a forgotten PIN;
  reset it in WhatsApp Manager instead.

> 🔐 Secret: our PIN is stored in GCP Secret Manager, not in this repo. Retrieve
> with:
> ```bash
> gcloud secrets versions access latest --secret=whatsapp-2fa-pin-prod \
>   --project=decent-genius-503000-h2 --account=support@cocoontimor.org
> ```
> (Create the secret if it does not exist yet: `gcloud secrets create whatsapp-2fa-pin-prod ...`)

## Command (reads creds from `.env`)

```bash
PID=$(grep -E '^WHATSAPP_PHONE_NUMBER_ID=' .env | cut -d= -f2- | tr -d '"'"'"'"'"')
TOKEN=$(grep -E '^WHATSAPP_ACCESS_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"'"'"')
curl -s "https://graph.facebook.com/v25.0/$PID/register" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messaging_product":"whatsapp","pin":"<6_DIGIT_PIN>"}'
```

Success response:
```json
{ "success": true }
```

## Find the correct Phone Number ID

The `register` edge needs the **Phone Number ID** (a ~15-digit Meta node ID),
**not** the dialable phone number. Look it up:

```bash
curl -s "https://graph.facebook.com/v25.0/{WABA_ID}/phone_numbers" \
  -H "Authorization: Bearer $TOKEN"
```

Each entry's `id` is the Phone Number ID. Also visible in
**App Dashboard → WhatsApp → API Setup** under the number.

## Errors seen & fixes

| Code | Meaning | Fix |
|------|---------|-----|
| `190` (subcode `463`) | Access token expired | Get a fresh token (App Dashboard → API Setup for 24h test, or a System User token for prod). See `whatsapp-webhook-setup.md`. |
| `12` (deprecated wall post) | `PHONE_NUMBER_ID` was the dialable number, not the Meta ID → invalid node/edge path | Set `WHATSAPP_PHONE_NUMBER_ID` to the real Phone Number ID (see lookup above). |
| `100` (Invalid parameter — "Unverified WABA") | The WhatsApp Business Account is not Business-verified | Complete Meta Business Verification (below), then rerun. |
| `133016` | >10 register attempts in 72h | Wait 72h; avoid PIN guessing. |

## Blocker: Business Verification (current status)

Last attempt returned `100 — Phone Link to WABA Failed - Unverified WABA`.
Token, Phone Number ID, and parameters are all correct; the WABA itself must be
verified first.

1. **Meta Business Suite → Settings → Business Info → Security Center**, or the
   Business Support Home link from the error.
2. Complete **Business Verification** (legal name, address, phone/website +
   documents; confirm via code). Review: minutes to a few business days.
3. When the WABA shows **Verified**, rerun the `register` call above.

Business Support Home:
<https://business.facebook.com/business-support-home/832786344056183/1021119610907506/>

## Related
- `docs/whatsapp-webhook-setup.md` — webhook config + where the two tokens come from.
- Config: `settings.WHATSAPP_PHONE_NUMBER_ID`, `settings.WHATSAPP_ACCESS_TOKEN`.
