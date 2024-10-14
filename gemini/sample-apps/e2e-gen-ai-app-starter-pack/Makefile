test:
	poetry run pytest tests/unit && poetry run pytest tests/integration

playground:
	poetry run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload & poetry run streamlit run streamlit/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false

backend:
	poetry run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

frontend:
	poetry run streamlit run streamlit/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false

load_test:
	poetry run locust -f tests/load_test/load_test.py -H $RUN_SERVICE_URL --headless -t 30s -u 60 -r 2 --csv=tests/load_test/.results/results --html=tests/load_test/.results/report.html

lint:
	poetry run codespell
	poetry run flake8 .
	poetry run pylint .
	poetry run mypy .
	poetry run black .
