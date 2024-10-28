FROM python:3.12-slim

WORKDIR /app

COPY ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/common
COPY common/config.yaml /app/common/

COPY ui/*.py .
COPY ui/pages /app/pages

EXPOSE 8080

ENV CONFIG_PATH=/app/common/config.yaml

CMD streamlit run --server.port 8080 --server.address 0.0.0.0 "$(ls *Home.py)"