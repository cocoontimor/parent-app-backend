# WhatsApp → View-Only App Access (Parent Mode)

Give parents read-only access to the Svelte app from WhatsApp: they text a
keyword, we reply with a magic link, the link logs them in, and they see only
their own **children**, **announcements**, and **payments**. No password, no
staff nav, no write actions.

## Why this is small

The read layer in `src/web/views.py` already scopes non-staff users to their own
family (`_children_qs`, `_circles_qs`, `_announcements_qs`) and every write is
gated by `_require_staff`. The work is: (1) a passwordless way in, (2) closing a
few read views that still return `.all()`, and (3) hiding staff UI from parents.

## Scope (confirmed)

- Parents view: **their children** (+ per-child update/photo timeline),
  **announcements**, **their payments**.
- **Not** in scope for parents: e-learning, messages log, urgent-alerts admin,
  users list, all create/edit actions.
- Delivery: **reply-to-inbound only** — parent texts a keyword, we reply with the
  link inside Meta's free 24h customer-service window (no template approval).

---

## Plan

### 1. Magic-link login (passwordless)  — `src/web/`

Use Django's built-in `django.core.signing` (no new dependency).

- **`src/web/tokens.py`** (new): 
  - `make_login_token(user)` → `signing.dumps({"uid": user.pk}, salt="parent-login")`.
  - `resolve_login_token(token, max_age)` → `signing.loads(...)` → `User` or `None`
    (catch `BadSignature` / `SignatureExpired`). Default `max_age` ~ 15 min.
- **`src/web/views.py`** (new view `magic_login`):
  - `GET /m/<token>/` → resolve token → `login(request, user)` → redirect to `/`.
    On failure render a small "link expired, text us again" page (reuse
    `Auth/Login` with an error prop, or a minimal `Auth/LinkExpired` page).
  - Set a longer session for parents: `request.session.set_expiry(60*60*24*30)`
    so they aren't kicked out daily.
- **`src/web/urls.py`**: add `path("m/<str:token>/", views.magic_login, name="magic-login")`.

Security notes: token is short-lived and single-purpose (salt-scoped); it carries
only the user id, signed with `SECRET_KEY`. Link travels over WhatsApp (parent's
own device). Optionally rotate by including `user.password`/`last_login` in the
signed value to invalidate old links — not required for v1.

### 2. Deliver the link over WhatsApp (keyword reply)  — `src/messaging/`

The current `send_whatsapp_message` only sends `type: "template"`. In-window
free-form replies need a plain-text send.

- **`src/messaging/services.py`** (new `send_text_message(recipient_phone, text)`):
  - POST `type: "text"`, `text: {"body": text}` to the same Graph endpoint with
    the bearer token. Mirror the credential fallback + logging of the existing
    sender. (No MessageLog template needed; log lightly or reuse MessageLog with
    a `template="text"` sentinel — decide during build.)
- **`src/messaging/views.py`** — in `_handle_inbound_message`, for `msg_type == "text"`:
  - Normalize `text.strip().lower()`; if it matches a keyword set
    (`{"menu", "app", "hi", "start"}` — finalize during build), and
    `sender` is a known non-staff user, build the link:
    `settings.APP_BASE_URL + reverse("magic-login", args=[make_login_token(sender)])`
    and `send_text_message(from_phone, "Tap to open your Cocoon: <link>")`.
  - Unknown sender → reply with a "we don't recognize this number" text (optional).
  - Keep the existing `InboundMessage` persistence untouched (runs after).
- **`src/cocoon/settings.py`**: add `APP_BASE_URL` (e.g. `https://cocoon.app`),
  read from env, used to build absolute magic links.

Note: the 24h window requires the parent to message us first — which is exactly
the keyword flow, so no template review is needed for v1.

### 3. Close read-leaks for non-staff  — `src/web/views.py`

These currently return `.all()` regardless of requester. For parents, scope or
deny:

| View | Current | Action for non-staff |
|---|---|---|
| `payments_index` | `FeePayment.objects...all()` | filter `child__in=_children_qs(user)` |
| `messages_index` | `MessageLog...all()` | deny (redirect `/`) — not in parent scope |
| `urgent_alerts_index` | `UrgentAlert...all()` | deny — not in parent scope |
| `elearning_*` | all courses/cohorts | deny — not in parent scope |
| `users_index` | already scoped to self | leave (or deny; harmless) |
| `dashboard`, `children*`, `announcements*` | already scoped | leave |

"Deny" = a small `@staff_page` guard (redirect non-staff to `/`). Add a helper
`_deny_non_staff(request)` and apply to the four admin-only read views. Verify
`children_show` and the dashboard only surface the parent's own child data.

### 4. Parent-mode UI  — `frontend/src/`

`auth.user.is_staff_group` is already injected by `web/middleware.py` but unused
in the nav.

- **`frontend/src/lib/Layout.svelte`**: when `!auth.user.is_staff_group`, render a
  trimmed sidebar (Home / My Children / Announcements / Payments) and hide
  staff-only links (Users, Messages, Urgent Alerts, E-Learning, Classes).
- On the pages parents can reach (`Children`, `Children/Show`,
  `Announcements/*`, `Payments/Index`): hide "Create"/action buttons behind
  `{#if auth.user.is_staff_group}`. Reads already come back scoped, so this is
  purely cosmetic/defense-in-depth on top of the server-side `_require_staff`.
- Rebuild the Vite bundle (`frontend/dist`) so django-vite serves the update in
  prod.

---

## Verification (per Karpathy goal-driven)

1. `resolve_login_token(make_login_token(u))` returns `u`; expired/tampered → `None`.
2. Hitting `/m/<valid>/` sets an authenticated session and lands on `/`.
3. Logged-in parent: `payments_index` shows only their children's payments;
   `messages_index` / `urgent_alerts` / `elearning` redirect to `/`.
4. Inbound webhook with `{type:"text", body:"menu"}` from a known parent →
   `send_text_message` called with a link containing a valid token (assert via
   the credential-fallback path / mock `requests.post`).
5. Frontend: parent session renders trimmed nav, no Create buttons; staff session
   unchanged.

## Rough effort

~1 focused session. Backend: `tokens.py` (~25 lines), `magic_login` (~20),
`send_text_message` (~30), keyword hook (~15), 4 view guards + 1 payment filter
(~20). Frontend: Layout branch + button guards (~40). Plus tests for 1–4.

## Deferred (not v1)

- Proactive link push (unprompted) — needs an approved Meta template with a
  dynamic URL button and a new send path.
- A dedicated `Parent/*` page namespace / bespoke parent UX (Option B).
- Link rotation/one-time-use tokens; rate-limiting the keyword reply.
