FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
RUN mkdir -p /app/staticfiles && chmod 777 /app/staticfiles && chmod +x entrypoint.sh \
    && DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
