# BigQuery MCP Agent Demo: Guided Walkthrough

Welcome! This tutorial will guide you through the setup and execution of your synthesized BigQuery MCP Agent demo.

## Prerequisites

Before we begin, ensure you have the necessary APIs enabled and the correct project selected.

<walkthrough-project-setup>
</walkthrough-project-setup>

### 🛠️ Set Your Project
Ensure your Cloud Shell is targeting the correct project:

<walkthrough-test-code-block>
gcloud config set project {{project-id}}
</walkthrough-test-code-block>

---

## Step 1: Provision Demo Environment in Your Project

The Demo Generator has synthesized a custom setup script for you. This script is responsible for provisioning the BigQuery dataset and setting up the agent code within YOUR GCP environment.

1. Go back to the **GE Demo Generator** Web UI.
2. Under **Step 3: Deploy**, click the **Copy** button next to the **Setup Script**.
3. **Paste the command** into the Cloud Shell terminal window (at the bottom of your screen) and press **Enter**.

> [!IMPORTANT]
> This app does not provision resources directly. Running this script is the required step to create the demo environment in your own project.

> **Note:** The script is uniquely named (e.g., `setup-demo-retail-inventory-831afa90.sh`) and creates a matching directory.

```bash
# Paste your setup command here in the terminal window below
```

---

## Step 2: Access Your Agent in Gemini Enterprise

Once the setup script from Step 1 completes, your agent is automatically deployed to Cloud Run and registered in Gemini Enterprise.

1. Open the [Gemini Enterprise Console](https://console.cloud.google.com/gemini-enterprise/apps) in your Google Cloud project.
2. Find your agent in the list and click to start a conversation.
3. You can verify the deployment status with:

```bash
gcloud run services list --filter="metadata.name:demo-" --format="table(name,region,status.url)"
```

---

## Step 3: Explore & Preview

Your agent is now live in Gemini Enterprise. Start a conversation directly from the [Gemini Enterprise Console](https://console.cloud.google.com/gemini-enterprise/apps).

#### 💡 Real-Time Data Viewer Application
If your setup included the Bento Grid operations console, the Data Viewer is automatically deployed as a Cloud Run Function. Look for the **Data Viewer URL** printed at the end of the setup script output.

> **Note (IAP-protected)**: The viewer is not public — it is protected by Identity-Aware Proxy, and only the deploying user is granted access automatically. **Open the viewer URL once in your browser before the demo** to complete Google sign-in. To let other people open it directly, add them with the `gcloud beta iap web add-iam-policy-binding` command printed in the setup summary (screen-sharing your own browser needs no extra grants).


---

## Step 4: Try the Scenarios

Use the **Step 4: Run Live Demo** section in your Demo Generator for tailored prompts.

**Example Prompts:**
- "Analyze sales trends using the BigQuery tool."
- "Correlate demographic data with real-world locations via Google Maps."
- "Update maintenance status on item #104 and post verification logs into Firestore."
- "Approve the flagged safety incident and update the operations grid instantly."


---

## 🛠️ Troubleshooting: Reliability in Cloud Run

If your agent occasionally stops responding or feels slow in Cloud Run:

### 1. Handling "Cold Starts"
Cloud Run may spin down instances after inactivity (cold starts). The first request after a break might take longer as it loads heavy libraries (like `pandas` or `scikit-learn`). 
- **Tip**: Sending the same prompt again usually works as the container is then "warm."
- **Solution**: For scaled usage, consider using a warmer service or reducing the number of heavy dependencies in your `requirements.txt`.

### 2. BigQuery Token Lags
Retrieving fresh auth tokens for BigQuery can sometimes add latency.
- **Fix Applied**: Our generated `tools.py` now includes stability patches that cache tokens for 30 minutes to ensure smooth tool execution.

### 3. Execution Timeouts
The default timeout for Cloud Run is 60 seconds. If your agent performs many sequential tool calls, it might hit this limit.
- **Optimization**: Use `gemini-3.1-pro-preview` for high-speed reasoning, and try to keep tool queries efficient.

### 4. 403 Insufficient Scope Errors
If you see "Request had insufficient authentication scopes" in the logs:
- **Solution**: Refresh your local credentials in Cloud Shell with mandatory scopes (Note: `maps-platform` is NOT a valid standalone scope; use `cloud-platform` instead):
  `gcloud auth application-default login --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/bigquery,openid,https://www.googleapis.com/auth/userinfo.email"`
- **Required Action**: After running the command, you MUST **restart the agent** (Ctrl+C and run the launch command again) to clear the cached tokens.

### 5. Cloud Run Deployment Failures (Org Policies)
If the setup fails to provision the Data Viewer application or the main Agent service:
- **Cause**: Many enterprise GCP Projects restrict unauthenticated endpoints via organization policies (like `constraints/iam.allowedPolicyMemberDomains`).
- **Mitigation**: The setup script is designed to print a warning and proceed even if the **Data Viewer** deployment fails due to ingress policies. You can still preview the multi-agent setup locally using `adk web` (Step 3).

### 6. 403 Permission Denied on Tool Invocation
If sub-agents fail to modify Firestore or pull from BigQuery:
- **Action**: Ensure the default Cloud Run Compute Service Account (`[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`) has been successfully provisioned with the following roles:
  - `roles/mcp.toolUser`
  - `roles/datastore.user` (For Firestore)
  - `roles/bigquery.dataViewer` & `roles/bigquery.jobUser`
  - `roles/aiplatform.user`


---

## 🧹 Cleanup: Removing Demo Resources

When you're done with your demo, you can easily clean up all created resources by running the setup script with the `--cleanup` flag:

```bash
# Replace with your actual script name
bash setup-demo-xxx.sh --cleanup
```

This will remove:
- **BigQuery Dataset**: The demo dataset and all its tables
- **Maps API Key**: The auto-generated API key for Google Maps
- **Local Directory**: The demo folder in your Cloud Shell home

> **Note:** You'll be prompted for confirmation before any resources are deleted.

---

### Need Help?
See the [GE Demo Generator README](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/search/gemini-enterprise/ge-demo-generator) or open an issue on the [GoogleCloudPlatform/generative-ai](https://github.com/GoogleCloudPlatform/generative-ai/issues) repository. Support is handled on a best-effort basis.
