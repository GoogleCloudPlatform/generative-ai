FROM python:3.11-slim

RUN pip install  --no-cache-dir poetry==1.6.1

RUN poetry config virtualenvs.create false

WORKDIR /code

COPY ./pyproject.toml ./README.md ./poetry.lock* ./

COPY ./app ./app

RUN poetry install  --no-interaction --no-ansi --no-dev

EXPOSE 8080

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]