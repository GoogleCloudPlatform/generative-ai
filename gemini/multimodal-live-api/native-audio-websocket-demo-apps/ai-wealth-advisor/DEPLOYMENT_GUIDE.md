# 🚀 Deployment Guide

The Financial Advisor application is designed to be deployed securely on Google Cloud Run. It uses a "double proxy" architecture where both the frontend and backend are private services, accessed via secure tunnels on your local machine.

## 📋 Prerequisites

1.  **Google Cloud Project:** You need an active GCP project with billing enabled.
2.  **Tools:**
    *   `gcloud` CLI (authenticated)
    *   `docker` (running locally)
    *   `task` (optional, for automated workflows)

## ⚙️ Configuration (Optional)

1.  **Initialize Environment File:**
    Create your local configuration file from the template.
    ```bash
    cp taskfile.env.sample taskfile.env
    ```

2.  **Customize Branding:**
    The application comes with generic defaults ("Financial Institution", "Advisor"). To customize the branding, edit `taskfile.env` and modify:
    *   `BANK_NAME`
    *   `ADVISOR_NAME`

## 🛠️ Deployment Instructions

We recommend using the **Taskfile** to automate the build and deploy process.

### Deployment Steps

1.  **Setup Infrastructure:**
    ```bash
    task infra:setup
    ```
2.  **Deploy Application:**
    ```bash
    task deploy:all
    ```

## 🔐 Accessing the Application

Since the services are private, you cannot access them via the public internet. You must start Cloud Run Proxy tunnels to forward traffic to your local machine.

1.  **Start Backend Tunnel (Terminal 1):**
    ```bash
    gcloud run services proxy financial-advisor-backend --port=8081 --region=us-central1
    ```

2.  **Start Frontend Tunnel (Terminal 2):**
    ```bash
    gcloud run services proxy financial-advisor-frontend --port=8080 --region=us-central1
    ```

3.  **Launch:**
    Open [http://localhost:8080](http://localhost:8080) in your browser.

## 🗣️ Sample Queries for the Financial Advisor

Once the application is running, you can interact with the AI assistant using natural language. Try these queries to test different capabilities:

**💰 Financial Education (RAG)**
*   "How does a 529 plan work?"
*   "What is the difference between stocks and bonds?"
*   "How do I reduce risk when investing?"
*   "How do I check the background of an investment professional?"

**📈 Real-Time Market Data (Tools)**
*   "What is the stock price of Google?"
*   "How is the Apple stock performing year-to-date?"
*   "Can you search what is an ETF?"


## 🧹 Clean Up

To remove the GCP resources created by this application (Service Account, GCS Bucket, Cloud Run Services), run the following command. Note that the Firestore database and the GCP Project itself will remain intact.

```bash
task infra:destroy
```