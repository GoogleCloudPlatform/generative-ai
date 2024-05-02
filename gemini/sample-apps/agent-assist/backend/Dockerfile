FROM python:3.9

WORKDIR /app/

COPY requirements.txt /app/

# Disable Pylint import checker
RUN pip install --no-cache-dir -r /app/requirements.txt # pylint: disable=wrong-import-position

COPY . /app/

WORKDIR /app/src/

EXPOSE 8000

ENTRYPOINT [ "gunicorn", "-w", "4", "--timeout", "0", "backend:app" ]
