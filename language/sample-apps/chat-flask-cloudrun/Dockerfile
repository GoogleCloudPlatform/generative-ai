FROM python:3.12

EXPOSE 8080
WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
