
# LLM EvalKit

## Summary

LLMEvalKit is a tool designed to help developers evaluate and improve the performance of Large Language Models (LLMs) on specific tasks. It provides a comprehensive workflow to create, test, and optimize prompts, manage datasets, and analyze evaluation results. With LLMEvalKit, developers can conduct both human and model-based evaluations, compare results, and use automated processes to refine prompts for better accuracy and relevance. This toolkit streamlines the iterative process of prompt engineering and evaluation, enabling developers to build more effective and reliable LLM-powered applications.

![Image](assets/image.gif)

**Authors: [Mike Santoro](https://github.com/Michael-Santoro), [Katherine Larson](https://github.com/larsonk)**


## 🚀 Getting Started

Start with this [notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/llmevalkit/prompt-management-tutorial.ipynb) this walk you through, running the application on a colab server.


## Application Workflow

Once you launch the application, you'll be directed to a home screen with the following options on the left-hand side:

* **New Prompt:** Create a new prompt.
* **Existing Prompt:** Edit an existing prompt.
* **Dataset Creation:** Upload and save datasets.
* **Evaluation Setup:** Set-up and launch an evaluation.
* **Evaluation Review:** Review Evaluation result.

***

## 1. New Prompt
### 📝 Creating a New Prompt

Follow these steps to create and save a new prompt using the Prompt Management page.

1.  **Define Prompt Details**

    You will need to define the following attributes for each new prompt:
    *   **Prompt Name:** A unique name to identify your prompt.
    *   **Prompt Text:** The core text of your prompt. You can use curly braces `{}` to denote variables or placeholder text that will be filled in later.
    *   **Model Name:** The specific Gemini model version you want to use for this prompt (e.g., `gemini-2.5-pro`).
    *   **System Instructions:** Optional instructions to guide the model's behavior and set its context before it processes the prompt.
    *   **Response Schema:** Define the desired structure for the model's output, such as a specific JSON format.
    *   **Generation Config:** A dictionary of generation parameters (like `temperature` or `max_output_tokens`) formatted as a string.
    *   **Prompt Task:** Select the most appropriate task type from the list: `Classification`, `Summarization`, `Translation`, `Creative Writing`, or `Q&A`.

    > **⚠️ Important:** After filling in the fields, you must click **Save Prompt** before proceeding.


2.  **Test Your Prompt**

    Once your prompt is saved, you can test it with sample data to see how the model responds.

    Your test input must be a JSON object where the keys exactly match the variable names (the text inside the `{...}`) that you defined in your **Prompt Text**. The values will be substituted into the prompt before it's sent to the model.

    **For example:**

    If your **Prompt Text** was:
    `"Draft a professional follow-up email to {contact_name} from {company_name} about our {product_name} solution."`

    Then, your sample user input should be a JSON object structured like this:

    ```json
    {
      "contact_name": "Jon Doe",
      "company_name": "Google",
      "product_name": "Project Alpha"
    }
    ```


## 2. Load Existing Prompt
### Loading and Editing an Existing Prompt

This section allows you to load a previously saved prompt, make modifications, and save your changes as a new version using the Prompt Management page.

1.  **Load Prompt**

    *   **Refresh List (Optional):** If you have recently created a new prompt and it doesn't appear in the dropdown, click the **Refresh List** button to update the list of available prompts.
    *   **Select Prompt & Version:** Choose your desired prompt from the "Select Existing Prompt" dropdown, then select a specific version from the "Select Version" dropdown.
    *   **Click Load Prompt:** Press the **Load Prompt** button. The page will populate with the details of the selected prompt version.

2.  **Edit Prompt Details & Test**

    *   Once loaded, you can freely edit any of the fields, such as the **Prompt Text**, **System Instructions**, or **Generation Config**.
    *   You can test your modifications at any time using the **Test Your Prompt** section.

3.  **Save as New Version**

    *   When you are satisfied with your changes, click the **Save as New Version** button.
    *   This action saves your edits as a new, incremental version of the prompt. For example, if you loaded `v2` and saved, your changes would be stored as `v3`, leaving the original `v2` untouched.

***

## 3. Dataset Creation
### 📂 Creating and Managing Datasets

This page allows you to upload your evaluation data to Google Cloud Storage (GCS). In this application, a **Dataset** is simply a folder within your GCS bucket that holds a collection of CSV documents.

#### Uploading a CSV File

1.  **Choose an Action:**
    *   Select **"Create a new dataset"** to make a new folder for your files.
    *   Select **"Add to an existing dataset"** to upload a file to a folder you've already created.

2.  **Specify the Dataset:**
    *   If creating a new dataset, enter a unique name for it in the text box.
        > **⚠️ Important:** After typing the name, you must press **Enter** for the application to register the new name.
    *   If adding to an existing one, simply select it from the dropdown list.

3.  **Upload the File:**
    *   Click "Browse files" to select a CSV file from your local machine.
    *   Press the **"Upload to Cloud Storage"** button to save the file. The page will automatically refresh to show the new dataset in the dropdown lists.

#### Viewing Existing Datasets

The second section on the page allows you to browse the datasets you have already created.

*   Select a dataset from the dropdown menu.
*   The application will then display a list of all the CSV filenames contained within that specific dataset folder.


## 4. 📊 Using the Evaluation Workbench

This workbench is a powerful tool for conducting both human and model-based evaluations of your prompts. The process is broken down into four main stages within the workbench.

#### 1. Setup & Configuration

First, you need to configure your evaluation session.

* **Dataset Selection:** Choose your dataset and the specific CSV document you want to analyze.
* **Sample Size:** Enter the number of samples from your dataset that you wish to evaluate manually.
* **Prompt Selection:** Select an existing prompt and its corresponding version from the dropdown lists.
> **⚠️ Important:** You must click the **Load Prompt** button to populate the workbench with your selected configuration before proceeding.
* **Feedback Type:** Define the rating system you will use for manual evaluation. Your options are:
    * `scale`: A numerical rating, typically 1-5.
    * `boolean`: A simple pass/fail or true/false rating.
    * `float`: A decimal rating between 0.0 and 1.0.

---

#### 2. Manual Rating & Inference

In this section, you will act as the human evaluator for the samples you selected.

You will be presented with a table containing the following columns for each sample:
* `UserInput`: The original input data from your dataset.
* `Ground Truth`: The ideal or correct response from your dataset.
* `Assistant Response`: The actual response generated by the LLM using your selected prompt.

Your tasks are:
1.  **Rate each response:** For every row, compare the `Assistant Response` to the `Ground Truth` and assign a score based on the **Feedback Type** you chose during setup.
2.  **Exclude samples (optional):** If an LLM response is irrelevant or not useful, you can uncheck the **Include in evaluation** box for that row. This will remove it from the final analysis.

Once you have rated all your samples, you can click the **Save Ratings to GCS** button to store your work in Google Cloud Storage.

---

#### 3. Auto-Rater Evaluation

This feature uses a separate "judge" model to automatically score the `Assistant Response` based on the `Ground Truth`, providing an objective, AI-driven perspective.

* **Select a Judge Model:** Choose the model you want to use as the evaluator from the dropdown list.
* **Customize the Judging Prompt:** A default prompt for the judge model is provided. You can modify this prompt to better align with your specific evaluation criteria if needed.
* **Launch the Evaluation:** Click the **Launch Auto Rater Evaluation** button.

The system will then process the samples and display the results, including a **Mean Gemini Judge Score** and your **Mean Human Score** for a side-by-side comparison.

---

#### 4. Auto-Rater vs. Human Analysis

The final section provides a detailed comparison between your manual ratings and the scores from the auto-rater.

This view includes a variety of metrics and visualizations (graphs) to help you analyze the results and understand how closely the LLM judge aligns with human evaluation.


## 5. 🚀 Launching Prompt Optimization


This step allows you to use an automated process to refine and improve your existing prompts based on a sample dataset.

#### 1. Initial Setup

First, configure the model and dataset for the optimization job.

* **Target Model & Prompt:**
    * Select the **target model** you want to optimize a prompt for.
    * Choose the **existing prompt** you wish to improve from the dropdown list.
    * Select the specific **version** of that prompt.
    > 📌 **Action:** Click the **Load Prompt** button to confirm your selection.

* **Evaluation Dataset:**
    * Select the CSV evaluation file. This file **must** contain `user_input` and `ground_truth` columns for the process to work.
    > 📌 **Action:** Click the **Load Dataset** button.

#### 2. Baseline Performance Evaluation

After loading the dataset, you need to establish a baseline performance score for your original prompt.

1.  **Generate Responses:** A preview of your dataset will appear. Select the **number of samples** you want to test against and click the **Generate Responses** button.

2.  **Review and Refine:** This populates the **Baseline Evaluation** section. A new `equals` column will appear next to the `truth` and `ground_truth` columns.
    * The tool will automatically count a response as "accurate" if it matches the ground truth.
    * You can manually review these matches and **uncheck any rows** where you disagree with the tool's assessment of a correct match.

3.  **Calculate Baseline:** Once you are satisfied with the review, click **Baseline Evaluation Results**. This will display the final performance metrics for your original prompt on this dataset.

#### 3. Starting the Optimization Job

With the baseline established, you are ready to start the automated optimization.

1.  **Launch:** Click the **Start Optimization Job** button.

2.  **Monitor:**
    > **⚠️ Please Note:**
    > * Prompt optimization is a long-running process that can take many minutes to complete.
    > * A warning message will appear at the top of the screen to confirm the job has started.
    > * To monitor the progress in real-time, **check the application's console logs**. You will find a direct URL to the detailed Google Cloud job logs there.

You can use the logs to determine when the optimization job has successfully completed and view the results.
Alternatively, by nagivating to Vertex AI > Model Development > Training in the console, you can also see the job status here. Make note of the job ID so you can reference in the last section.

### Step 6: 🏆 Reviewing Optimization Results

The **Results Browser** is where you can view and compare the outcomes of your completed prompt optimization jobs.

To review your results, **select the optimization job** you wish to analyze from the dropdown menu. The jobs are identified by the unique **Job ID** generated in the previous step.

After you select a job, the page will display the results. You will see a list of the different prompt versions created by the optimizer, along with the **percentage accuracy** each one achieved on the evaluation dataset. This allows you to easily identify the best-performing prompt.

> **📌 Important Notes & Troubleshooting**
>
> * **Job Duration:** Please be aware that a prompt optimization job can take **15-20 minutes** to complete.
>
> * **Check Job Status:** You can monitor the live status of your job in the Google Cloud console here:
>     [Vertex AI Custom Jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs)
>
> * **Troubleshooting Errors:** If an optimization job fails, you can find detailed logs in your GCS staging bucket. Look for an `error.json` file within the specific job's output directory. The path will be similar to this:
>     `gs://<your-gcs-bucket>/optimization/<job-id>/optimization_jobs/<detailed-job-name>/error.json`



## License
```
Copyright 2025 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language
```
