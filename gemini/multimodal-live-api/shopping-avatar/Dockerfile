# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY ecommerce/frontend/package*.json ./
RUN npm ci
COPY ecommerce/frontend/ ./
RUN npm run build

# Stage 2: Build the FastAPI backend and serve everything
FROM python:3.11-slim
WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies via uv
COPY ecommerce/backend/pyproject.toml ecommerce/backend/uv.lock ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

# Copy backend files
COPY ecommerce/backend/ ./

# Copy built frontend assets to /app/frontend/dist so main.py can serve them
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set environment variables and expose port
ENV PORT=8080
EXPOSE 8080

# Run Uvicorn serving fastapi on 0.0.0.0:8080
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
