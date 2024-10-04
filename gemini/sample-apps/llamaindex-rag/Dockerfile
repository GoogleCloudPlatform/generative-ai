FROM python:3.12-slim

WORKDIR /app

# Combine RUN instructions and address warnings
RUN pip install --no-cache-dir poetry==1.5.1 && \
    apt-get update && \
    apt-get install --yes --no-install-recommends gcc=4:10.2.1-1 g++=4:10.2.1-1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy 
COPY common /app/common
COPY src /app/src
COPY ui /app/ui

# Expose the port your FastAPI app will run on 
EXPOSE 8080

# Command to run the FastAPI app 
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]