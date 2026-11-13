FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN SECRET_KEY=x DB_ENGINE=sqlite python manage.py collectstatic --noinput
CMD ["sh","-c","python manage.py migrate && gunicorn config.wsgi:application -b 0.0.0.0:8000 --workers 3"]
