#!/bin/bash
set -e

python manage.py migrate --no-input
# Reassert the Celery Beat schedule from the declarative fixture on every deploy.
python manage.py loaddata periodic_tasks --no-input
python manage.py collectstatic --no-input
exec gunicorn cocoon.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout=120 \
    --workers=3 \
    --threads=2 \
    --log-level=info
