# Use a slim Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy your app code
COPY . .

# Expose port 8080
EXPOSE 8080

# Command to start Gunicorn with your Flask app
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "4", "app:app"] 
