#!/usr/bin/env bash
# Runs the Vite dev server (Svelte/Inertia, HMR) and Django's runserver
# together. Django serves pages; django-vite pulls assets from Vite in dev.
set -euo pipefail

cd "$(dirname "$0")"

if [ -f venv/bin/activate ]; then
  source venv/bin/activate
elif [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(cd frontend && npm run dev) &
pids+=($!)

(cd src && python manage.py runserver) &
pids+=($!)

wait -n
