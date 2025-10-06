# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED True

# Copy the dependencies file and install them
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Get the port number from the environment variable
ENV PORT 8080

# Expose the port the app runs on
EXPOSE $PORT

# Define the command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "main:app"]
