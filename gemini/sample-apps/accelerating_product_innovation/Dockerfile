FROM python:3.10.11

# Allow statements and log messages to immediately appear in the Knative logs
# ENV PYTHONUNBUFFERED True

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y


# Copy local code to the container image.


WORKDIR /app
COPY ./app ./

EXPOSE 8080

# Run the web service on container startup

ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8080", "--server.address=0.0.0.0"]