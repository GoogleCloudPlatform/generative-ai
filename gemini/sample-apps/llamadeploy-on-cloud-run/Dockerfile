FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PROJECT_ID "[your-project-id]"
ENV LOCATION = "[your-project-location]"
ENV FIRESTORE_DATABASE_ID "[your-firestore-database-id]"
ENV DATA_DIRECTORY "/app/data" 

COPY interact.py .
COPY core.py .
COPY workflow.py .
COPY wrapper.sh .

#Create a directory for data
RUN mkdir /app/data

# Copy the data into the directory
COPY ./data /app/data

# Make the wrapper script executable
RUN chmod +x wrapper.sh

CMD ["./wrapper.sh"]