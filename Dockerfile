FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY src_python /app/src_python

WORKDIR /app/src_python

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

WORKDIR /app

CMD ["sh", "-c", "uvicorn src_python.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
