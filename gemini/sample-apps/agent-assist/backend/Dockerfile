FROM python:3.9

WORKDIR /app/

COPY requirements.txt /app/

RUN python -m venv venv

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

RUN /app/venv/bin/activate

ENV PYTHONPATH=/app

WORKDIR /app/src/

EXPOSE 8000

ENTRYPOINT [ "gunicorn", "-w", "4", "--timeout", "0", "backend:app" ]