# Cocoon — WhatsApp Engagement Plan

*Parent-facing layer · Dili, Timor-Leste · June 2026*

---

## WhatsApp Pricing (Rest of Asia Pacific)

| Category | Per message | When charged |
|---|---|---|
| **Service** | **FREE** | Parent messages first → 24h window to reply free |
| **Utility** | $0.014 | Outside 24h window (but **free inside** the window) |
| **Marketing** | $0.086 | Always charged — avoid this category entirely |
| **Authentication** | $0.014 | Always charged |

Key rules:
- When a parent messages you, you get a **free 24h window** for unlimited free-form replies AND free utility templates.
- Marketing templates are always charged. Everything Cocoon sends is transactional/utility — never categorise as marketing.
- Per-message billing (not per-conversation) since July 2025.

---

## Cost Optimisation: Daily Digest Pattern

**Core idea:** Batch all pending items (updates, reminders, permission slips) into a single daily digest. Send ONE utility template → parent taps "View" → system delivers everything in the free service window.

**Without batching:** 6 items = 6 × $0.014 × 220 parents = $18.48
**With batching:** 1 template × $0.014 × 220 parents = $3.08

Same content. 83% cheaper.

### Monthly cost estimates (~220 parents)

| Pattern | Cost |
|---|---|
| Daily digest | 220 × $0.014 × 30 = **$92/mo** |
| Weekly digest | 220 × $0.014 × 4 = **$12/mo** |
| Crisis alert (ad hoc) | **$3.08** each |
| Parent-initiated (milestones, suggestions) | **$0** |

### What skips the digest (sent immediately)
- **Crisis alerts** — standalone utility template + SMS fallback
- **Time-sensitive permission slips** — if due within hours

---

## UX Flow: Digest

```
┌──────────────────────────────────┐
│  📬 Cocoon School                │
│  You have 6 new items:           │
│  • 1 update                      │
│  • 2 reminders                   │
│  • 3 permission slips            │
│                                  │
│  ┌────────┐                      │
│  │ View   │                      │
│  └────────┘                      │
│                                  │
│        You tapped: View          │
│                                  │
│  ── UPDATE ──────────────────    │
│  [Photo of Aria painting]        │
│  Aria painted in art class       │
│  today and helped tidy up.       │
│                                  │
│  ── REMINDER 1 ──────────────    │
│  📅 Sports Day — June 28, 9AM   │
│  Bring water and a hat.          │
│  ┌────────────────────┐          │
│  │ 📎 sports-day.ics  │          │
│  └────────────────────┘          │
│                                  │
│  ── REMINDER 2 ──────────────    │
│  📅 Parent Meeting — July 1     │
│  3:00 PM in the main hall.       │
│                                  │
│  ── PERMISSION 1 ────────────    │
│  Field trip to Christo Rei       │
│  July 2, 8:30 AM – 2:00 PM      │
│  ┌───────────┐  ┌──────────┐    │
│  │ Approve ✓ │  │ Decline  │    │
│  └───────────┘  └──────────┘    │
│                                  │
│       You tapped: Approve ✓      │
│                                  │
│  ── PERMISSION 2 ────────────    │
│  Swimming lesson July 5          │
│  ┌───────────┐  ┌──────────┐    │
│  │ Approve ✓ │  │ Decline  │    │
│  └───────────┘  └──────────┘    │
│                                  │
│       You tapped: Approve ✓      │
│                                  │
│  ── PERMISSION 3 ────────────    │
│  Photo consent for newsletter    │
│  ┌───────────┐  ┌──────────┐    │
│  │ Approve ✓ │  │ Decline  │    │
│  └───────────┘  └──────────┘    │
│                                  │
│       You tapped: Decline        │
│                                  │
│  ✅ All done! 2 approved,        │
│  1 declined. Have a good day.    │
└──────────────────────────────────┘
```

---

## UX Flow: Standalone Features

### Crisis alert (immediate, never batched)
```
┌──────────────────────────────────┐
│  🚨 URGENT: Early Pickup         │
│                                  │
│  Due to flooding, school is      │
│  closing at 11:00 AM today.      │
│  Please collect your child       │
│  as soon as possible.            │
│                                  │
│  Call +670 XXX XXXX if you       │
│  cannot collect.                 │
└──────────────────────────────────┘

 + SMS sent simultaneously
```

### Milestones (parent-initiated, free)
```
┌──────────────────────────────────┐
│           You: MILESTONES        │
│                                  │
│  🌟 Aria's Milestones            │
│                                  │
│  ✅ Counting to 20 (May 15)      │
│  ✅ Writing her name (May 22)    │
│  ✅ Sharing with peers (June 3)  │
│  🔄 Tying shoelaces (in progress)│
│                                  │
│  View full history:              │
│  https://cocoon.app/m/abc123     │
└──────────────────────────────────┘
```

### Suggestion box (parent-initiated, free)
```
┌──────────────────────────────────┐
│           You: SUGGEST           │
│                                  │
│  📝 What would you like to       │
│  suggest? Type your message.     │
│                                  │
│  You: Could we have more         │
│  outdoor activities?             │
│                                  │
│  ✅ Thank you! Your suggestion   │
│  has been received.              │
└──────────────────────────────────┘
```

---

## Backend: Digest Queue Design

```
Guardian
  └── PendingQueue (items accumulate throughout the day)
        ├── Update (photo, text)
        ├── Reminder (event ref)
        ├── Reminder (event ref)
        ├── PermissionSlip (needs response)
        ├── PermissionSlip (needs response)
        └── PermissionSlip (needs response)

Scheduled job (e.g. 3PM daily):
  1. For each guardian with pending items → send ONE digest template
  2. Guardian taps "View" → webhook fires → 24h window opens
  3. System sends items in sequence with short delays
  4. Interactive items (permissions) wait for tap before sending next
  5. Mark items as delivered
```

---

## Feature Build List

### Phase 0 — Prerequisites
- [ ] Meta Business account verification + WhatsApp number registration
- [ ] Webhook endpoint (signature validation, verification challenge)
- [ ] Submit message templates for approval (digest, crisis alert)
- [ ] SMS fallback provider with Timor-Leste coverage
- [ ] GCP project: Cloud Run, Cloud SQL, GCS, Secret Manager

### Phase 1 — Core Models + Messaging Engine
- [ ] Data models: Guardian, Child, Class, Teacher (phone = WhatsApp identity key)
- [ ] Guardian opt-in capture and consent tracking
- [ ] Outbound send service: template sends + free-form replies via Cloud API
- [ ] MessageLog with per-recipient delivery status (sent/delivered/read/failed)
- [ ] PendingQueue + digest scheduler (Celery beat / Cloud Scheduler)
- [ ] Celery fan-out with retries for broadcasts
- [ ] Django Admin dashboard for teachers/staff

### Phase 2 — Parent-Facing Features (via digest)
- [ ] Child updates & photos: teacher posts → GCS media → queued for digest
- [ ] Announcements: queued for digest with urgency tiers
- [ ] Event reminders: Event model, .ics generation, queued for digest
- [ ] Permission slips: interactive buttons, immutable consent records, queued for digest
- [ ] Crisis alert: immediate parallel WhatsApp + SMS blast (bypasses digest)

### Phase 3 — Parent-Initiated Features (free)
- [ ] Milestone viewing: keyword trigger → summary reply (or PWA link)
- [ ] Voice notes: inbound audio download + GCS storage, outbound Tetum audio
- [ ] Suggestion box: keyword trigger, pseudonymised storage

### Cross-Cutting
- [ ] Tetum-first template content (+ Portuguese/English variants)
- [ ] Media handling: upload/download against Cloud API, GCS storage, signed URLs
- [ ] Cost tracking dashboard (template sends by category, monthly spend)
- [ ] Delivery observability: per-recipient status tracking
