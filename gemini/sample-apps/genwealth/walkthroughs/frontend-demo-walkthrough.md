# GenWealth Application - Front End Demo

This demo will showcase how you can combine the data and documents you already have and the skills you already know with the power of AlloyDB AI, Vertex AI, Cloud Run, and Cloud Functions to build trustworthy Gen AI features into your existing applications.

We’ll walk through an end-to-end “Knowledge Worker Assist” use case for a fictional Financial Services company called GenWealth. GenWealth, a subsidiary of Cymbal Investments, is an investment advisory firm that combines personalized service with cutting-edge technology to deliver tailored investment strategies to their clients that aim to generate market-beating results.

In this scenario, we’ll be adding 3 new Gen AI features to GenWealth’s existing Investment Advisory software:

1. First, we’ll improve the Investment Search experience for GenWealth’s Financial Advisors with semantic search powered by AlloyDB AI.

1. Second, we’ll build a Customer Segmentation feature for GenWealth’s Marketing Analysts to identify prospects for new products and services.

1. Third, we’ll build a Gen AI chatbot that will supercharge productivity for GenWealth’s Financial Advisors.

## Walkthrough

### Pre-Work

Imagine you are a Financial Analyst, and you need to analyze a Prospectus [like this](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/sample-prospectus/RYDE.pdf) for an upcoming IPO.

You're expected to create a company overview, a stock analysis, and determine a buy/sell/ or hold rating for this new security. You could comb through the 191-page prospectus and draft something from scratch, or you can use Gen AI to jumpstart your effort.

You can simply drop that file into the `$PROJECT_ID-docs` bucket in GCS to kick off a pipeline of Cloud Functions that perform the steps listed below.

> NOTE: This pipeline was already executed on a few sample files when you ran `install.sh`. You can drop another PDF document like this into the `$PROJECT_ID-docs` bucket to see the pipeline in action.

1. Extract text from the PDF using Document AI.

1. Chunk the text with LangChain.

1. Generate embeddings for each chunk and store the chunks and embeddings in the `langchain_vector_store` table AlloyDB.

1. Generate an investment overview, analysis, and a buy/sell/hold rating with Vertex AI.

1. Write the generated results to the `investments` table in AlloyDB.

The data for the `RYDE` prospectus and related tables looks something like this (results may vary slightly due to generated content).

> NOTE: You can explore the application and document data yourself by logging into pgAdmin as described in the [Back End Demo Walkthrough](../walkthroughs/backend-demo-walkthrough.md) guide.

1. Document chunks in the `langchain_vector_store` table:

   ![Document Chunks](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/2-document-chunks.png "Document Chunks")

1. Generated `overview` and embeddings in the `investments` table:

   ![Overview](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/3-overview.png "Overview")

1. Summary of buy ratings for > 8500 tickers in `investments` table:

   ![Investments](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/4-investment-table-summary.png "Investments")

1. User profile data, including bios and embeddings.

   ![User Profiles](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/5-user-profiles.png "User Profiles")

So now that you've extracted all of this useful data from your prospectus, how can you use it to improve your existing Advisory Services software? Let's explore a few use cases in the GenWealth UI.

### Accessing the GenWealth UI

Access the GenWealth Advisory Services UI by navigating to the Cloud Run endpoint you provisioned earlier with the [`install.sh`](../install.sh) script. You can retrieve the URL by running the following command in Cloud Shell.

```bash
cd && cd generative-ai/gemini/sample-apps/genwealth/
source ./env.sh
gcloud run services describe genwealth --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID
```

You should see an Investment Search UI like the one shown below.

![GenWealth Interface](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/1-genwealth-interface.png "GenWealth Interface")

### Semantic Search for Investments

Imagine you're a Financial Advisor, and you're searching for investments that can help your client beat the market in a high inflation environment.

Previously, you would log into the GenWealth Advisory Services UI and perform a keyword search. Try it out by executing a query like the one below.

![Keyword Search](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/6-keyword.png "Keyword Search")

Notice that your result set is pretty limited and gives you mixed results. One result recommends a TIPS product that guarantees a real return, but your other result is an ETF that tracks an economy that is currently facing high inflation that investors may want to hedge against.

Click **See Query** to view the simple SQL query used to retrieve these results. Just because the keywords I was looking for exist in the `analysis` field, it doesn't mean that those are the results I'm actually looking for. This highlights the deficiencies of a simple keyword-based search approach.

![Keyword Query](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/7-keyword-query.png "Keyword Query")

Now click the **Semantic Search** radio button and run the same query, as shown in the screenshot below. Notice that the SQL query changes, and it's now using Gen AI embeddings to run a semantic search on the `analysis` field.

![Semantic Search](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/8-semantic-search.png "Semantic Search")

Notice that your result set is much better - your first result is an ETF that is specifically built to benefit from high inflation! Semantic search in AlloyDB AI is powered by Gen AI embeddings models in Vertex AI, and it understands not just what you ask, but also what you **mean** by what you ask.

Just like that, you've added your first Gen AI feature to our Advisory Services software, leveraging the powerful integrations between AlloyDB AI and Vertex AI, using the data you already have and the skills you already know (SQL).

### Customer Segmentation

Now imagine you're a GenWealth Marketing Analyst, and you want to find prospective clients who may be interested in a new Bitcoin ETF you just launched. GenWealth prides itself on personalized service, so you can't just spam your entire client list advertising the new product.

You can leverage the data you already have about your users (bio data in the `user_profiles` table) to run semantic search using Gen AI embeddings with AlloyDB AI to find prospective clients.

Navigate to the **Prospects** tab in the GenWealth UI, and run a query like the one shown below.

![Prospect Search](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/9-prospect-search.png "Prospect Search")

You immediately get a pretty good result set of prospective clients that you should reach out to about your new product.

Click **See Query** to view the SQL query that generates this result. Notice that you're using the embeddings() function once again to leverage Gen AI embeddings in Vertex AI and vector similarity search in AlloyDB AI to run a semantic query against your relational database.

![Embeddings Query](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/10-query.png "Embeddings Query")

Click the drop-down arrow next to your first result (Geoffrey Folmer) to read his bio. He's a young entrepreneur with a high risk appetite, and he already invests in a small amount of cryptocurrency.

![Bio](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/11-folmer.png "Bio")

Notice that your query didn't say anything about "Bitcoin" or "cryptocurrency", but the query semantically understood the type of investor you were looking for.

These results are pretty good, but if you scroll down, you'll notice that there are some clients in the result set who have a low risk appetite, and others who might be too close to retirement age for this to be a good recommendation. To solve for that, we need to refine our semantic search results with keyword filters. This technique is called Hybrid Search, and in AlloyDB AI, it is as simple as adding a WHERE clause to our semantic query.

Click the **Filters** toggle to refine your search to only return results with a high risk profile and a specific age range.

![Hybrid Search](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/12-hybrid-search.png "Hybrid Search")

Notice the query was updated to combine semantic similarity search with keyword search.

![Hybrid Query](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/13-hybrid-query.png "Hybrid Query")

With that, you have created your second Gen AI feature, and you now have a tailored result set of prospects that you can reach out to regarding our new Bitcoin ETF.

### Grounded Gen AI Email Responder

Imagine you're a Financial Advisor again, and you took last week off. When you get back in on Monday, your inbox is flooded with questions from clients. GenWealth prides itself on personalized service, so you can’t just reply with a canned response. Each of these emails is going to require you to research the client’s portfolio, financial goals, and preferences before responding.

For example, let’s say that you got an email from Donya Bartle asking a question about investing an inheritance she just received.

Refresh your screen and search for Donya Bartle in the Prospects interface to view her profile.

![Donya Bartle](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/14-bartle.png "Donya Bartle")

Notice that she has a low risk profile, and she has a goal of saving for a down payment on a home within 7 years.

> NOTE: Take note of Donya's user id (`90`) so that you can use it on the next screen.

You could manually draft a response to the emails and all 200+ other emails like it that are waiting for you in your inbox, or you could use Gen AI to generate a personalized response for you.

Navigate to the **Ask** interface and click the **Advanced** toggle. Click the arrows in each field shown below to auto-populate the prompt and a few parameters, as shown in the screenshot below.

![Donya Bartle](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/16-email.png "Donya Bartle")

Click **Ask** and review the result. It should look similar to the output below.

> NOTE: Your results may vary slightly due to the dynamic nature of Gen AI text completion models.

![Donya Bartle](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/17-emailresult.png "Donya Bartle")

How did we get such a personalized result? Click **View Query** to see how we injected Donya's user bio into the input of our [llm() function](../database-files/genwealth-demo_llm.sql), and click **See Prompt** to view the enriched prompt that our llm() function generated on the user's behalf before sending it to the Vertex AI LLM for text completion. Here we are using the data we already have about our users to ground the prompt, and we are inferencing an LLM directly from the database using a simple SQL function.

Now you can rinse and repeat for each user who emailed you while you were on vacation. For example, update the prompt with a new email from Geoffrey Folmer. He heard about your new Bitcoin ETF and proactively reached out to you to learn more.

Copy/paste the following email into the prompt, and update the User ID to `638`.

```text
Hi Paul,

I just heard about your new Bitcoin ETF. Do you think I should move some money out of my index funds and into that ETF?

Thanks,
Geoffrey Follmer
```

![Geoffrey Folmer](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/19-second-email.png "Geoffrey Folmer")

### Grounded Gen AI Chatbot with Guardrails

The email responder is a great way to supercharge productivity for GenWealth's Financial Advisors, but what if you wanted to make this chatbot functionality available directly to GenWealth's customers as a first step before reaching out to an advisor?

If you work in financial services, you know that chatbots aren't allowed to provide financial advice due to regulatory requirements. You'll have to implement some guardrails to prevent the bot from violating that restriction. To do this, you'll add two parameters to your llm() function call:

1. You will add response restrictions that instruct the model not to give financial advice.

1. While the response restrictions are helpful, they still rely on the model to honor the request. This isn't deterministic enough for your regulators, so you will also append a deterministic legal disclaimer to the end of every response.

Update your inputs as shown in the screenshot below, and review the results.

![Guardrails](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/genwealth-ui/20-guardrails.png "Guardrails")

Notice that the response is still personalized to Donya (it knows her name and mentions her low risk tolerance), but it now warns that it can't give financial advice, offers general information, and appends a legal disclaimer to the end of the response.

### Query Document Chunks

Finally, imagine you're now a Financial Analyst, and you want to ask natural language questions about the text in the prospectus that you uploaded earlier. Because we stored the chunks and embeddings of those chunks in AlloyDB AI (`langchain_vector_store` table), we can query those chunks and ask Gemini to use the most revelant chunks as context to answer a question.

Navigate to the **Research** tab. Select a ticker and ask a natural language question like, "How will the IPO proceeds be used?".

Notice that this interface shows two results. On the left-hand side, you see a response generated by Vertex AI Agent Builder - the easiest way to get started with document processing and understanding. On the right-hand side, you see a response that's directly querying the database and answering the question with Gemini. There are pros and cons to each approach, and you can use both together based on your use case.

## Summary

In this demo, you built new Gen AI features into your existing application, including semantic search, customer segmentation, and a Gen AI chatbot. You also learned how to query your relational database using semantic query concepts.

If you'd like to learn more about the internals of this application, explore the [Back End Demo Walkthrough guide](./backend-demo-walkthrough.md) to get hands-on with the code.
