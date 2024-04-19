FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

RUN apt-get update
RUN apt-get install g++-6 -y
RUN apt-get install gcc -y


COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt


# Copy local code to the container image.


WORKDIR /app
COPY ./app ./

EXPOSE 8501

# Run the web service on container startup

ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]

#this if for prod