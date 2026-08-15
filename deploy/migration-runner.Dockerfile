FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir SQLAlchemy==2.0.36 psycopg2-binary==2.9.9

COPY scripts/apply_migrations.py /app/scripts/apply_migrations.py
COPY db/migrations /app/db/migrations

CMD ["python", "scripts/apply_migrations.py"]
