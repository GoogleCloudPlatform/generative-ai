FROM python:3.10-slim

WORKDIR /app
RUN pip install poetry
RUN apt-get update && apt-get install --yes --no-install-recommends gcc g++

COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

# Copy 
COPY common /app/common
COPY src /app/src
COPY ui /app/ui



# Expose the port your FastAPI app will run on 
EXPOSE 8080

# Command to run the FastAPI app 
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
