FROM python:3.9

# Set environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set the working directory
WORKDIR /app/

# Copy and install requirements
COPY requirements.txt /app/
RUN python -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Change working directory to src
WORKDIR /app/src/

# Expose the port
EXPOSE 8000

# Define the entry point
ENTRYPOINT [ "gunicorn", "-w", "4", "--timeout", "0", "backend:app" ]
