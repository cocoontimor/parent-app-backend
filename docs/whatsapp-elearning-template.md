# WhatsApp `elearning_lesson` Template

The drip job (`elearning.tasks.release_due_lessons`) sends each released lesson
as a WhatsApp **template** message with a "Mark as watched" quick-reply button.
Template messages must be pre-approved by Meta before they can be sent, and the
button must exist on the approved template. This runbook covers creating it.

## What the message needs

- **One body variable** `{{1}}` — receives the composed lesson text (title,
  course, YouTube link). Matches `send_whatsapp_message(..., variables=[body])`.
- **One quick-reply button** — labelled "Mark as watched". Its per-message
  payload is set by us to `WATCHED:<lesson_release_id>` (see
  `elearning/services.py`); when the parent taps it, WhatsApp posts an inbound
  `button` message back to our webhook carrying that payload, and
  `record_completion()` records a `LessonCompletion`.

## Option A — WhatsApp Manager UI

1. WhatsApp Manager → **Account tools → Message templates → Create template**.
2. Category: **Utility** (a course-delivery notification, not marketing).
3. Name: `elearning_lesson` · Language: **English**.
4. **Body** (Meta rejects a bare `{{1}}` or a leading/trailing variable, so it is
   sandwiched in fixed text — this is what was submitted):
   ```
   A new lesson from Cocoon.

   {{1}}

   Tap Mark as watched below once you have finished the lesson. Thank you.
   ```
   Add a single-line sample value for `{{1}}` so it passes review.
5. **Buttons → Quick reply**, button text: `Mark as watched`.
6. Submit. Approval is usually minutes; the template must be **Approved** before
   the drip job can send it.

## Option B — Graph API

```
POST https://graph.facebook.com/v21.0/{WABA_ID}/message_templates
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "name": "elearning_lesson",
  "language": "en",
  "category": "UTILITY",
  "components": [
    { "type": "BODY", "text": "A new lesson from Cocoon.\n\n{{1}}\n\nTap Mark as watched below once you have finished the lesson. Thank you.", "example": { "body_text": [["New lesson: Intro ..."]] } },
    { "type": "BUTTONS", "buttons": [ { "type": "QUICK_REPLY", "text": "Mark as watched" } ] }
  ]
}
```

`{WABA_ID}` is the WhatsApp Business Account ID (not the phone number ID).

## How the tap comes back

The button's payload is set **per send** (not baked into the template) via the
message's `components`:

```json
{ "type": "button", "sub_type": "quick_reply", "index": 0,
  "parameters": [ { "type": "payload", "payload": "WATCHED:<release_id>" } ] }
```

On tap, Meta calls our webhook (`/webhooks/whatsapp/`) with an inbound message:

```json
{ "from": "<parent_phone>", "type": "button",
  "button": { "text": "Mark as watched", "payload": "WATCHED:<release_id>" } }
```

`messaging.views._handle_inbound_message` routes any `WATCHED:` payload to
`elearning.services.record_completion`, which matches the release + parent and
upserts a `LessonCompletion` (idempotent — repeat taps don't double-count).

## Fallback without approval

If credentials are unset the send is logged as a `FAILED` MessageLog instead of
calling Meta (see `send_whatsapp_message`), so local/dev work needs no template.
Completion counts surface per lesson on the course page in the admin UI.
