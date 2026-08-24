FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
ENV PORT=8080
# Shell form on purpose: Cloud Run injects $PORT, and JSON form would not
# expand it.
# hadolint ignore=DL3025
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app
