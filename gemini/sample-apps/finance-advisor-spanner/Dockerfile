FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["streamlit", "run", "Home.py", "--server.enableCORS", "false", "--browser.serverAddress", "0.0.0.0", "--browser.gatherUsageStats", "false", "--server.port", "8080"]
