# Robust Load Testing for Generative AI Applications

This directory provides a comprehensive load testing framework for your Generative AI application, leveraging the power of [Locust](http://locust.io), a leading open-source load testing tool.

## Local Load Testing

Follow these steps to execute load tests on your local machine:

**1. Start the FastAPI Server:**

Launch the FastAPI server in a separate terminal:

```bash
poetry run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

**2. (In another tab) Create virtual environment with Locust**
Using another terminal tab, This is suggested to avoid conflicts with the existing application python environment.

```commandline
python3 -m venv locust_env && source locust_env/bin/activate && pip install locust==2.31.1
```

**3. Execute the Load Test:**
Trigger the Locust load test with the following command:

```bash
locust -f tests/load_test/load_test.py \
-H http://127.0.0.1:8000 \
--headless \
-t 30s -u 60 -r 2 \
--csv=tests/load_test/.results/results \
--html=tests/load_test/.results/report.html
```

This command initiates a 30-second load test, simulating 2 users spawning per second, reaching a maximum of 60 concurrent users.

**Results:**

Comprehensive CSV and HTML reports detailing the load test performance will be generated and saved in the `tests/load_test/.results` directory.

## Remote Load Testing (Targeting Cloud Run)

This framework also supports load testing against remote targets, such as a staging Cloud Run instance. This process is seamlessly integrated into the Continuous Delivery pipeline via Cloud Build, as defined in the [pipeline file](cicd/cd/staging.yaml).

**Prerequisites:**

- **Dependencies:** Ensure your environment has the same dependencies required for local testing.
- **Cloud Run Invoker Role:** You'll need the `roles/run.invoker` role to invoke the Cloud Run service.

**Steps:**

**1. Obtain Cloud Run Service URL:**

Navigate to the Cloud Run console, select your service, and copy the URL displayed at the top. Set this URL as an environment variable:

```bash
export RUN_SERVICE_URL=https://your-cloud-run-service-url.run.app
```

**2. Obtain ID Token:**

Retrieve the ID token required for authentication:

```bash
export _ID_TOKEN=$(gcloud auth print-identity-token -q)
```

**3. Execute the Load Test:**
The following command executes the same load test parameters as the local test but targets your remote Cloud Run instance.

```bash
poetry run locust -f tests/load_test/load_test.py \
-H $RUN_SERVICE_URL \
--headless \
-t 30s -u 60 -r 2 \
--csv=tests/load_test/.results/results \
--html=tests/load_test/.results/report.html
```
