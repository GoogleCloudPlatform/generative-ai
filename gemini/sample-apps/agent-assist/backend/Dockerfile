FROM python:3.9

WORKDIR /app/

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

WORKDIR /app/src/

EXPOSE 8000

ENTRYPOINT [ "gunicorn", "-w", "4", "--timeout", "0", "backend:app" ]