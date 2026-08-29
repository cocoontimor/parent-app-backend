# Cocoon Infrastructure (Cloud Run)

OpenTofu/Terraform for the Cocoon backend on GCP, following the
`equilux/eq-infra` conventions.

## Architecture

- **Cloud Run service** `cocoon-backend-production` — the Django/Inertia web app
  (gunicorn). Public, autoscaling, `min_instances=0` by default. No nginx
  (WhiteNoise serves static; Cloud Run terminates TLS).
- **Cloud SQL (Postgres)** — attached via Unix socket at `/cloudsql/<conn>`.
- **Cloud Run Jobs** — same image, command overridden:
  - `cocoon-migrate-production` → `manage.py migrate` (run each deploy).
  - `cocoon-daily-digest-production` → `manage.py run_daily_digest`.
  - `cocoon-release-lessons-production` → `manage.py release_lessons`.
- **Cloud Scheduler** — the clock. Triggers the two task Jobs (daily 15:00 Dili;
  hourly, with per-cohort `send_hour` gating delivery). No Celery, no Redis.
- **Secret Manager** — `SECRET_KEY`, DB password, WhatsApp token/app-secret/verify-token.

```
Cloud Scheduler ──OAuth──▶ Cloud Run Job ──socket──▶ Cloud SQL
   (cron)                   (manage.py …)
Browser / WhatsApp ───────▶ Cloud Run service ──────▶ Cloud SQL
```

## Layout

```
infra/
├── modules/
│   ├── cloud-run/         # web service (v2, cpu_idle, cloudsql, probes)
│   ├── cloud-run-job/     # migrate + task jobs
│   ├── scheduler-job/     # Cloud Scheduler -> Job trigger (+ run.invoker)
│   └── secrets/           # Secret Manager + accessor IAM
└── environments/production/
```

## Bootstrap (one time)

Run by an operator with project admin (not the CI SA). `gcloud config set
project decent-genius-503000-h2` first.

1. **Fill the unknowns** in `environments/production/variables.tf`:
   `cloudsql_connection_name` (`gcloud sql instances describe <name>
   --format='value(connectionName)'`), `gs_bucket_name`, `whatsapp_phone_number_id`.

2. **State bucket:**
   ```bash
   gcloud storage buckets create gs://cocoon-prod-terraform-state \
     --project=decent-genius-503000-h2 --location=asia-southeast1 \
     --uniform-bucket-level-access
   gcloud storage buckets update gs://cocoon-prod-terraform-state --versioning
   ```

3. **Push the first image** (Cloud Run can't be created without one):
   trigger the GitHub Actions `Build & Deploy` workflow once — it builds/pushes
   `…/backend:prod` and then skips deploy (service doesn't exist yet).

4. **Apply:**
   ```bash
   cd environments/production
   tofu init
   tofu apply
   ```
   This creates the service, jobs, scheduler, service accounts, and secret
   *resources*.

5. **Set secret values** (never stored in TF state):
   ```bash
   for s in secret-key postgres-database-password whatsapp-access-token \
            whatsapp-app-secret whatsapp-webhook-verify-token; do
     printf '%s' "REPLACE" | gcloud secrets versions add "cocoon-$s-production" \
       --project=decent-genius-503000-h2 --data-file=-
   done
   ```

6. **Migrate + smoke test:**
   ```bash
   gcloud run jobs execute cocoon-migrate-production --region=asia-southeast1 --wait
   curl -sS "$(tofu output -raw service_url)/health/"
   ```

## Domain cutover (`app.cocoontimor.org`)

Map the domain to the service (verify domain ownership first). Cloud Run domain
mapping availability varies by region; if unsupported in `asia-southeast1`, front
it with an external HTTPS load balancer + serverless NEG instead. Flip DNS only
after the health check and a login smoke test pass on the `.run.app` URL. Then
retire the old VM (`cocoon-prod-backend`) and its nginx.

## Ongoing deploys

`git push` to `main` → GitHub Actions builds the image, runs the migrate Job to
completion, rolls out the service, and updates the task Jobs' image. Terraform
`ignore_changes` on the image means TF and CI don't fight over it.

## Deviations from eq-infra

- Reuses the **existing** Artifact Registry repo (`cocoon-prod`) and WIF setup
  rather than managing them here.
- No `celery-vm` / Memorystore — scheduled work runs as Cloud Run Jobs on Cloud
  Scheduler (right-sized for two cron tasks + one synchronous urgent-alert send).
