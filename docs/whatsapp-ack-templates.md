# WhatsApp `daily_digest` & `urgent_alert` Templates — Acknowledge Button

Both notifications are sent as **template** messages with a single quick-reply
button so the parent can confirm receipt. The button must exist on the approved
template, otherwise the send (which includes a button component) is rejected by
Meta. This runbook covers adding it. See `whatsapp-elearning-template.md` for the
same pattern applied to lessons.

## What each message needs

- **One body variable** `{{1}}` — receives the composed digest / alert text.
  Matches `send_whatsapp_message(..., variables=[body])`. **Meta will not accept
  a body that is only `{{1}}`, nor a variable at the very start or end** — the
  variable must be sandwiched between fixed text (header + footer), and there
  must be enough fixed words relative to the variable ("parameter words ratio").
- **One quick-reply button** — label "Got it". Its per-message payload
  is set by us to `ACK:<message_log_id>` when the sender passes `acknowledge=True`
  (see `messaging/services.py`). When the parent taps it, WhatsApp posts an
  inbound `button` message to our webhook and `record_acknowledgment()` stamps
  `MessageLog.acknowledged_at` for that exact message.

## Approved template bodies (as submitted)

These are the exact bodies created in the "Cocoon" WABA (`1021119610907506`).
Header/footer are fixed; `{{1}}` is the composed message.

**`daily_digest`** (button: `Got it`)
```
Hello from Cocoon.

{{1}}

This is an automated daily update from your centre. Please tap Got it below to confirm you have seen it. Thank you.
```

**`urgent_alert`** (button: `Got it`)
```
Important notice from Cocoon.

{{1}}

Please tap Got it below to confirm you have seen this urgent message. Thank you.
```

## WhatsApp Manager UI (equivalent)

For each: **Create template** → Category **Utility** → Language **English** →
**Body** = the text above (with a single-line sample for `{{1}}`) →
**Buttons → Quick reply** = `Got it` → Submit. Must be **Approved** before sending.

## Notes

- The payload is set **per send**, not baked into the template — the approved
  template only needs the button to *exist*.
- Delivery and read receipts are tracked separately via the `statuses` webhook
  (`MessageLog.status` → `delivered` / `read`); the button records an explicit
  human acknowledgement on top of that.
- Without credentials configured, `send_whatsapp_message` logs instead of
  calling Meta, so local/dev work needs no template.
