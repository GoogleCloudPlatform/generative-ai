# Vertex AI Search Grounded Generation Playground

This demo showcases how to use Vertex AI [Grounded Generation API](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen) with a Next.js frontend. It provides a user-friendly interface for exploring both chat-based and side-by-side comparisons of grounded and ungrounded responses. This allows you to test different models and grounding sources, including [Google Search](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen#web-grounding) and [Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen#inline-vais).

## What is Grounded Generation?

The [Grounded Generation API](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen) addresses a key limitation of foundational Large Language Models (LLMs): their reliance on data frozen at the time of training. This means LLMs are unaware of recent information and can't access your private enterprise data, leading to potential inaccuracies or "hallucinations." Grounding connects LLMs to live, relevant data, significantly improving the factuality and usefulness of their responses.

With RAG, we can retrieve relevant information from external sources (like Google Search or your private data) before passing the user's query to the LLM. This additional context allows the model to generate grounded, factual responses.

## Why Grounding is Important

- **Increased Accuracy and Factuality:** Grounded responses are based on verifiable information, reducing hallucinations and improving trustworthiness.
- **Access to Live and Private Data:** Grounding allows LLMs to use the latest web data and your enterprise's internal knowledge, enabling them to answer questions they couldn't otherwise.
- **Improved Relevance:** By providing context, grounding ensures responses are more relevant to the user's specific needs and situation.
- **Transparency and Verifiability:** Grounded responses include source citations, allowing users to easily verify the information and explore the original sources for deeper understanding.
- **Cost Optimization (Dynamic Retrieval):** Dynamic retrieval minimizes costs by only using external search when necessary.
- **Differentiation:** Grounding your LLM with your private data allows you to create differentiated AI experiences tailored to your business needs.

## Grounded Generation Playground Features

- **Chat Interface:** Engage in interactive conversations with the model, utilizing grounded generation for more factual and informative responses. The chat maintains session context, so follow-up questions can build upon previous interactions and retrieved data. This showcases the grounding in [multiple turns of a conversation capability](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen#multi-turn-generation) of the Grounded Generation API.
- **Comparison Mode:** Directly compare grounded and ungrounded responses side-by-side to see the impact of grounding on accuracy and relevance. This clearly demonstrates the benefits of grounding for various query types.
- **Model Selection:** Choose from different Gemini models, including those specifically optimized for higher factuality and groundedness.
- **Grounding Source Selection:** Toggle between different sources:

  - **Google Search:** Access up-to-date information from the web.
  - **Vertex AI Search:** Ground responses using your private enterprise data stored in Vertex AI Search. This enables tailored, context-aware responses based on your internal knowledge.
  - **Custom Sources:** Integrate other search engines (like ElasticSearch) or databases via cloud functions. This offers flexibility and allows you to leverage your existing search infrastructure.
  - **Third-party Data (Coming Soon):** Google is collaborating with partners like Moody's, Thomson Reuters, and MSCI to provide access to curated, authoritative data sources.

- **Retrieval Threshold (Dynamic Retrieval):** Control when Google Search is used with an adjustable threshold. This dynamic retrieval optimizes cost and latency by only performing web searches when the model's existing knowledge is insufficient. This is a crucial feature for cost-effective, real-world applications.
- **Code Examples:** View JavaScript, Python, and cURL examples for interacting with the Grounded Generation API, simplifying integration into your own projects.

## Local Development

1. **Prerequisites:**

   - Node.js and npm (or yarn/pnpm) installed.
   - A Google Cloud project with the Vertex AI API enabled.
   - Set up authentication: The app uses Application Default Credentials. Run `gcloud auth application-default login`.
   - Set environment variables (see below).

2. **Clone the repository:**

   ```bash
   git clone REPOSITORY
   cd grounded-generation-playground
   ```

3. **Install dependencies:**

   ```bash
   npm install
   ```

4. **Set environment variables:**

   Modify the `.env` file with your project details.

   ```bash
   PROJECT_ID=your-google-cloud-project-id
   PROJECT_NUMBER=your-google-cloud-project-number
   LOCATION=your-google-cloud-project-location (e.g., us-central1)
   ```

   Replace the placeholders with your actual project details. You can find your project number in the Google Cloud Console project settings.

5. **Run the development server:**

   ```bash
   npm run dev
   ```

   The app will be accessible at [http://localhost:3000](http://localhost:3000).

## Deployment to Google Cloud

This application can be deployed to Google Cloud using either App Engine or Cloud Run. Both methods are detailed below. The provided `app.yaml` file is configured for App Engine.

### App Engine Deployment

1. **Prerequisites:**

   - gcloud CLI installed and configured with your project.

2. **Setup Environment Variables:**

   - Modify the `app.yaml` file to set the correct project ID, location, and project number.

3. **Deploy:**
   From the root directory of the project, run:

```bash
gcloud app deploy
```

This will deploy the application to App Engine. The deployed URL will be displayed after the deployment is complete.

## Contributing

Contributions are welcome! Please see the `CONTRIBUTING.md` file for details.

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
