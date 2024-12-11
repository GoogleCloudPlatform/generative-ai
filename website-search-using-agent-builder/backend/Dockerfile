FROM python:3.11
COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
RUN mkdir -p /code
WORKDIR /code
COPY . /code/

ENV BIG_QUERY_DATASET=""
ENV FRONTEND_URL=""

EXPOSE 8080
ENTRYPOINT ["gunicorn", "main:app", "--workers=4", "--worker-class=uvicorn.workers.UvicornWorker", "--timeout=36000","--bind=0.0.0.0:8080"]