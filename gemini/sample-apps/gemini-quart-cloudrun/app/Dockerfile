# Use a slim Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose port 8080
EXPOSE 8080

# Run hypercorn
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8080"]