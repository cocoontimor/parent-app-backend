FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m app
USER app
WORKDIR /home/app/src

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ /home/app/src/
COPY entrypoint.sh /home/app/entrypoint.sh

EXPOSE 8000

# Default command (overridable by compose for celery/beat). Runs migrations,
# collects static, then serves gunicorn on $PORT (default 8000).
CMD ["bash", "/home/app/entrypoint.sh"]
