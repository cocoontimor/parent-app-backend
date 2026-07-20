#!/bin/bash
set -e

python manage.py migrate --no-input
python manage.py collectstatic --no-input
exec gunicorn cocoon.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout=120 \
    --workers=3 \
    --threads=2 \
    --log-level=info
