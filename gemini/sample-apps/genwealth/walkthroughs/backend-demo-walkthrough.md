# GenWealth Application - Back End Demo

You are a SQL Developer for a Financial Services company called Generative Wealth Management ("GenWealth"). GenWealth is an Investment Advisory firm with a strong reputation for combining personalized service with cutting-edge technology to deliver tailored investment strategies. They serve thousands of clients across North America, empowering them to reach their financial goals.

You have been tasked with building the following Generative AI features into GenWealth's core Advisory Services software:

1. Improve the Investment Search experience for GenWealth's Financial Analysts by replacing basic Keyword Search with more expressive Semantic Search powered by Gen AI embeddings.

1. Create a Customer Segmentation feature using Gen AI embeddings and Vector Similarity Search to help Gen Wealth's Marketing Analysts identify target customers for new product campaigns.

1. Build the backend for a RAG-powered AI Chatbot that uses existing customer and product data to provide personalized financial advice.

The Advisory Services application was recently migrated to GCP, with the front end and middleware services running on Cloud Run, and the PostgreSQL database running on AlloyDB - a fully managed PostgreSQL-compatible database service that combines the best of Open Source with the best of Google to provide 4x OLTP performance, 10x vector search performance, 100x OLAP performance, and AI-powered engine autotuning.

Due to your familiarity with PostgreSQL, you would like to build the new Gen AI features without having to learn a new database technology or programming language, so you decided to leverage AlloyDB AI's direct integration with Vertex AI to develop LLM-powered features using familiar SQL semantics.

## Setup pgAdmin

### Login to pgAdmin

1. Run the command below in Cloud Shell to get the url for the pgAdmin interface.

   ```bash
   # Get the URL for the pgAdmin web server
   cd && cd generative-ai/gemini/sample-apps/genwealth/
   source ./env.sh
   echo "http://$(gcloud compute instances describe pgadmin --format='get(networkInterfaces[0].accessConfigs[0].natIP)' --zone=$ZONE)/pgadmin4"
   ```

1. Copy and paste the URL from the previous step into a web browser on your local machine. You should see an interface like the screenshot below.

   > NOTE: Use http, not https. Our test environment has not been configured for SSL/TLS.

   ![pgAdmin Login Interface](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/1-login.png "pgAdmin Login Interface")

1. Login to pgAdmin. The user name is `demouser@genwealth.com`. The password is the pgAdmin password you chose when you setup the environment. If you forgot the password, you can retrieve it from Secret Manager by running the following command in Cloud Shell.

   ```bash
   cd && cd generative-ai/gemini/sample-apps/genwealth/
   source ./env.sh
   gcloud secrets versions access latest --secret="pgadmin-password-${PROJECT_ID}"
   echo ""
   ```

1. You should now see an interface like the one below.

   ![pgAdmin Interface](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/2-interface.png "pgAdmin Interface")

### Connect to AlloyDB

1. Right-click on Servers under Object Explorer, and select Register > Server.

   ![Register Connection](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/3-register.png "Register Connection")

1. Enter a friendly name like “AlloyDB” in the Name field, then switch to the Connection tab.

   > NOTE: You can ignore the warning that says “Either Host name or Service must be specified”. We will enter that information next.

   ![Register Server](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/4-general.png "Register Server")

1. In the Connection tab:

   - Enter the AlloyDB Private IP address you wrote down earlier in Step 3.1.
   - Update the Username to `postgres` and enter the password you set for the AlloyDB cluster when you provisioned the environment. If you forgot the password, you can retrieve it by running the following command in Cloud Shell:

   ```bash
   cd && cd generative-ai/gemini/sample-apps/genwealth/
   source ./env.sh
   gcloud secrets versions access latest --secret="alloydb-password-${PROJECT_ID}"
   echo ""
   ```

   - Enable the Save password toggle.
   - Click Save.

   Your Connection tab should look like the screenshot below.

   ![Connection](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/5-connection.png "Connection")

### Explore the pgAdmin Interface

1. Click the drop-down arrow next to Servers, then do the same for AlloyDB, Databases, and ragdemos.

   ![Object Explorer](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/6-tree.png "Object Explorer")

1. Right-click the ragdemos database, then click Query Tool.

   ![Query Tool](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/7-querytool.png "Query Tool")

1. Enter the SQL query below in the Query Tool and then click the Execute button to run it.

   ```SQL
   SELECT COUNT(*) FROM investments;
   ```

1. This Query Tool interface is where you will run all of the SQL queries provided in the rest of this demo. Notice a few things about the interface:

   - There is a connection drop-down list that shows you which database you’re connected to. In this case, we’re connected to the ragdemos database as the postgres user on the AlloyDB instance.
   - When you click Execute (), the Query Tool will execute everything in the query by default. To only run one block of code at a time, you can select the text you want to execute before clicking the Execute button.
   - The results of your query show up in the Data Output grid at the bottom of the interface.
   - There is a Scratch Pad on the right side of the interface that you can use to keep notes. This will be a useful space to copy and paste the enriched prompts and LLM responses we will generate later, because it provides more room to explore the output.

   ![Query Interface](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/8-queryinterface.png "Query Interface")

### Configure pgAdmin Preferences

We will be working with lots of text data in this demo, so it is useful to limit the width of output columns in the results grid for readability.

1. Click File > Preferences.

   ![Preferences](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/9-preferences.png "Preferences")

1. Scroll down in the Preferences pane and select Results grid.

1. Set Maximum column width to 200 as shown in the screenshot below, then click Save.

   ![Grid Preferences](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/10-grid.png "Grid Preferences")

The pgAdmin setup is complete! You will now start building your Gen AI features for the Advisory Services software.

## Build Gen AI Features using SQL

It’s time to build your Gen AI Features! As a reminder, you are a SQL Developer for GenWealth who has been tasked with building the following Generative AI features into GenWealth's core Advisory Services software:

1. Improve the Investment Search experience for GenWealth's Financial Analysts by replacing basic Keyword Search with more expressive Semantic Search powered by Gen AI embeddings.
1. Create a Customer Segmentation feature using Gen AI embeddings and Vector Similarity Search to help Gen Wealth's Marketing Analysts identify target customers for new product campaigns.
1. Build the backend for a RAG-powered AI Chatbot that uses existing customer and product data to provide personalized financial advice.

### Explore the Test Data

1. Return to your pgAdmin interface and open a new query window connected to the ragdemos database.

1. Run the following SQL queries one at a time in pgAdmin to explore the data in your investments and user_profiles tables.

   > NOTE: The data in the investments and user_profiles tables is all synthetic and was generated by the text-bison PaLM model via AlloyDB AI’s integration with Vertex AI.

   ```SQL
   ---- Explore the test data ----

   -- Investments table (tracks 8541 distinct tickers)
   SELECT COUNT(*) FROM investments LIMIT 5;
   SELECT * FROM investments LIMIT 5;

   -- Count of investment ratings
   SELECT rating, COUNT(*) AS rating_count
   FROM investments
   GROUP BY rating;

   -- User profiles table
   SELECT COUNT(*) FROM user_profiles; -- 2000 customers
   SELECT * FROM user_profiles LIMIT 5;
   ```

1. Notice that the investments table contains overview and analysis data for over 8500 stock tickers. The user_profiles table contains basic user information, including names, ages, risk profiles, and bios.

1. Notice that the investments table has embeddings for the overview and analysis columns, and the user_profiles table has embeddings for the bio column. These embeddings were generated by the Google PaLM textembeddings-gecko model via AlloyDB AI’s integration with Vertex AI, and we will use them later to perform semantic search with pgvector similarity search.

### Improve the Investment Search Experience

Today, Financial Analysts use a simple Query Builder interface like the one shown below to search through investments using basic keywords. The interface sends a SQL query to the database and returns basic and sometimes unreliable results.

You will leverage AlloyDB AI’s vector similarity search capabilities to enhance this experience with semantic search powered by the Google PaLM Gen AI [textembedding-gecko](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings) model in Vertex AI.

![Query Builder](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/11-querybuilder.png "Query Builder")

Follow the steps below to build the new Gen AI feature.

1. Imagine you are a Financial Analyst who is trying to find investments for your client that are expected to perform well in a high-inflation environment. You would go into the UI and use the query builder, which would generate a basic SQL query like the one below, using naive keyword search with SQL’s LIKE syntax.

   Run the SQL query below to see the results users get with basic keyword search today.

   ```SQL
   -- Search for stocks that might perform well in a high inflation environment
   -- using naive keyword search with LIKE:

   SELECT ticker, etf, rating, analysis
   FROM investments
   WHERE analysis LIKE '%hedge%'
   AND analysis LIKE '%high inflation%'
   LIMIT 5;
   ```

1. Take a closer look at the analysis column in your first result, ticker INN_B.

   > NOTE: It may be useful to double-click on the result and copy/paste it into the Scratch Pad for easier viewing, as shown in the screenshot below.

   ![INN_B](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/12-inflation.png "INN_B")

1. Notice that this is an investment that tracks an economy that is currently experiencing high inflation, and investors may want to hedge against that risk. Our query returned the result because the analysis contains the words “hedge” and “high inflation”, even though this is not an investment we would want to recommend to a client specifically looking for investments that perform well in high-inflation markets.

1. Now you will update the SQL query to use AlloyDB AI’s vector similarity search to do semantic search on the analysis_embedding column using the same terms. You will also use AlloyDB AI’s built-in [embedding() function](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings#generate) to translate the search string into an embedding so that you can compare it to the existing embeddings in the analysis_embedding column.

   ```SQL
   -- Search for stocks that might perform well in a high inflation environment
   -- using semantic search with Gen AI embeddings
   SELECT ticker, etf, rating, analysis,
       analysis_embedding <=> embedding('textembedding-gecko@003', 'hedge against high inflation') AS distance
   FROM investments
   ORDER BY distance
   LIMIT 5;
   ```

1. Take a look at the analysis column, and notice that this time you get much better results. The semantic query used Gen AI embeddings to understand what you meant, not just what you said. Your first result, HZN, is an investment that is designed specifically to benefit from high inflation, and the rest of the results would also be good recommendations that you could provide to your client.

### Add a Customer Segmentation Feature

GenWealth’s Marketing Analysts have requested a better way to identify target customers for their new products and services. They want to conduct targeted advertising campaigns to increase conversion rates and to avoid annoying customers that they know are unlikely to be interested in a particular product. GenWealth’s customers pay a premium for personalized, boutique service, and a mass email wouldn’t be effective or well-received.

You will leverage AlloyDB AI’s vector similarity search capabilities to identify target customers using semantic search powered by the Google PaLM Gen AI textembeddings-gecko model in Vertex AI. You will also enable hybrid search by allowing analysts to narrow their semantic search results with metadata filters.

Users will access the customer segmentation feature using a UI similar to the one below. The application will generate a SQL query based on the user’s inputs, and the database will do the rest.

![Prospect Finder](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/13-prospectfinder.png "Prospect Finder")

Follow the steps below to build the new Gen AI feature.

#### Semantic Search

1. Imagine you are a Marketing Analyst, and you want to find prospective customers for a new Bitcoin ETF that GenWealth just launched. You could use the UI to enter the Search Term “young aggressive investor” to start your search.

1. Run the query below to see the results of this search. This query executes a semantic search by using AlloyDB AI’s embedding() function to translate the search string into an embedding and then comparing it to the embeddings in the user_profile.bio_embedding column via vector similarity search.

   ```SQL
   -- Use similarity search with Gen AI embeddings to find potential customers for a new Bitcoin ETF
   SELECT first_name, last_name, email, age, risk_profile, bio,
       bio_embedding <=> embedding('textembedding-gecko@003', 'young aggressive investor') AS distance
   FROM user_profiles
   ORDER BY distance
   LIMIT 50;
   ```

1. Take a look at the bio column, and notice that your first result is a young entrepreneur named Geoffrey Follmer who has a high risk appetite and already has a small investment in cryptocurrency. Your query didn’t mention anything about Bitcoin or cryptocurrency, but the semantic search understood the type of investor you were looking for.

1. Most of the results are of similar quality, but you notice that at least 2 of your results include clients with medium and low risk tolerances (Gino Cardwell and Melissa Pullum). You also notice that some of the results are for clients who are too close to retirement age to get good candidates for this particular investment.

#### Hybrid Search (Semantic Search + Keyword Filtering)

1. While the semantic query gave you pretty good results with minimal effort, you would like to refine your results by filtering out clients with medium and low risk tolerances, as well as clients who are close to retirement age. This technique is called Hybrid Search, and it combines the power of semantic search with the ability to limit results based on metadata and tags.

1. Hybrid Search can be complex to implement in some vector databases, but since you’re building this feature using SQL in AlloyDB, all it takes to enable Hybrid Search is a simple WHERE clause.

1. Run the query below to see your new list of potential customers for your new product.

   ```SQL
   -- Add a WHERE clause to narrow results using Hybrid Semantic + Keyword Search
   SELECT first_name, last_name, email, age, risk_profile, bio,
       bio_embedding <=> embedding('textembedding-gecko@003', 'young aggressive investor') AS distance
   FROM user_profiles
   WHERE risk_profile = 'high'
       AND age BETWEEN 18 AND 50
   ORDER BY distance
   LIMIT 50;
   ```

You have now built your first two Gen AI features using just SQL!

### Build a RAG-Powered Gen AI Chatbot

GenWealth would like to build a new Gen AI chatbot to provide clients with 24/7 access to financial education, account details, and basic information related to budgeting, saving, and different types of investments. GenWealth guards their brand and reputation very carefully, and they don’t want to risk deploying a chatbot that might give their customers factually incorrect information (i.e. “hallucinate”).

You will write a PostgreSQL function that takes a user’s prompt and enriches it with data from your application database to improve the accuracy and trustworthiness of the chatbot’s output. The function will send the enriched prompt to the Google PaLM text-bison model using AlloyDB AI’s integration with Vertex AI, and it will return the LLM response to the user.

Users will interact with the chatbot using a UI similar to the one below. The application will generate a SQL query based on the user’s prompt, and the database will do the rest.

![Chatbot](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/14-chat.png "Chatbot")

Follow the steps below to build the new Gen AI feature.

#### Explore the llm() function

1. Run the query below to view the definition of the llm() function. You can copy and paste the results into a new query window or text editor to read through the code.

   ```SQL
   -- Show llm() function definition
   SELECT pg_get_functiondef(oid)
   FROM pg_proc
   WHERE proname = 'llm';
   ```

1. Notice that the function takes in a set of parameters, which it uses to enrich the user’s prompt. At the end of the function, it makes a call to the text-bison LLM in Vertex AI using the [ml_predict_row() function](https://cloud.google.com/alloydb/docs/ai/invoke-predictions).

   ![Predict](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/15-predict.png "Predict")

1. Run the query below to execute a basic llm() call.

   ```SQL
   -- Generic prompt example
   SELECT llm_prompt, llm_response
   FROM llm(prompt => 'I have $25250 to invest. What do you suggest?');
   ```

1. Take a look at the llm_prompt column, and notice that we’ve added a few things to the user’s prompt with our function. We gave the AI and User a role, gave the model specific instructions, passed in the user’s prompt, and added an empty <CONTEXT> block and a generic <RESPONSE_RESTRICTIONS> block. We’ll add context and restrictions into these blocks in the next few examples.

   ![Enriched Prompt](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/16-enriched.png "Enriched Prompt")

1. Now take a look at the llm_output column. Our prompt is still somewhat generic, so the output is unsurprisingly a bit generic as well.

   > NOTE: Your specific output may differ due to the dynamic nature of LLMs.

   ![Text Completion](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/17-textcompletion.png "Text Completion")

   > NOTE: If you work in Financial Services, you probably know that chatbots aren’t actually allowed to give financial advice, and this output sounds really close to giving financial advice. Don’t worry - We’ll address that in Step 5.

#### Add Branding and Roles

1. Now we’ll do a bit of prompt engineering to improve our output. The user is still only responsible for entering the prompt into the UI, but we’ll do some additional prompt enrichment by clarifying the AI’s role and adding a mission and output branding instructions.

1. Read through the llm_role, mission, and output_instructions parameters in the query below to understand the instructions we’re passing to the model, then run the query and view the llm_response output.

   ```SQL
   -- Give the AI a role, a mission, and output branding instructions
   SELECT llm_prompt, llm_response
   FROM llm(
       -- User prompt
       prompt => 'I have $25250 to invest. What do you suggest?',

       -- Prompt enrichment
       llm_role => 'You are a financial chatbot named Penny',
       mission => 'Your mission is to assist your clients by providing financial education, account details, and basic information related to budgeting, saving, and different types of investments',
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and "GenWealth" company affiliation.'
   );
   ```

1. Notice that the recommendations are now more detailed, and the signature line contains GenWealth branding. The recommendations are still a little generic, which we’ll fix by adding some user context later. But first, let’s see what happens when we change the mission.

#### Change the Mission

1. Every parameter matters! Read through the query below, and notice that everything is the same as the last query, except that we changed the mission. Run the query and take a look at the llm_output.

   ```SQL
   -- Every parameter matters! Change the mission to see the impact.
   SELECT llm_prompt, llm_response
   FROM llm(
       -- User input
       prompt => 'I have $25250 to invest. What do you suggest?',

       -- Prompt enrichment
       llm_role => 'You are a financial chatbot named Penny',
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and "GenWealth" company affiliation.',

       -- Change mission
       mission => 'Your mission is to give sarcastic financial advice that no one should ever take seriously or implement in the real world'
   );
   ```

1. Notice that the output has changed completely, both in the tone and quality of the content. This highlights how important every piece of context that you enrich a prompt with really is.

#### Enrich The Prompt With User Profile Data

1. So far we’ve only done static prompt enrichment, which has given us better results, but it’s still not a personalized experience. We have lots of data about our users, so let’s use RAG to enrich the prompt with information about the current user to create a tailored output.

   Let’s say that the current user is Donya Bartle. Run the query below to explore her information, and pay particular attention to her bio.

   ```SQL
   -- View user information for Donya Bartle
   SELECT * FROM user_profiles
   WHERE id = 90;
   ```

1. Now run the query below to get a personalized recommendation from Penny to send back to the chat interface with Donya.

   > NOTE: We have reverted the change to our mission parameter.

   ```SQL
   -- Tell the LLM what we know about the user
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 90
   )
   SELECT llm_prompt, llm_response, bio
   FROM profile, llm(
       -- User input
       prompt => 'I have $25250 to invest. What do you suggest?',

       -- Prompt enrichment
       llm_role => 'You are a financial chatbot named Penny',
       mission => 'Your mission is to assist your clients by providing financial education, account details, and basic information related to budgeting, saving, and different types of investments',
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and "GenWealth" company affiliation.',

       -- Add user information via RAG
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       additional_context => CONCAT(E'<BIO>', bio, E'</BIO>')
   )
   ```

1. Notice that the response is now very specific to Donya. We greet her by name, we mention her low risk tolerance, and we provide a recommendation based on her 7-year timeline for a down payment on a new home.

#### Add Guardrails

Uh oh! You reviewed your new chatbot functionality with GenWealth’s business stakeholders, and while they were impressed by the functionality, it turns out that chatbots aren’t allowed to give financial advice due to regulatory requirements. In this step, you will add guardrails to prevent Penny from providing financial advice, keeping your regulators and your customers happy.

1. Review the query below and notice that we have updated the llm_role and mission for Penny, and we have also added a response_restrictions parameter. Run the query and review the results. Notice that Penny now provides a warning that she cannot provide financial advice, but she can still provide some general advice that is personalized to the customer.

   ```SQL
   -- Add response restrictions
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 90
   )
   SELECT llm_prompt, llm_response, bio
   FROM profile, llm(
       -- User input
       prompt => 'I have $25250 to invest. What do you suggest?',

       -- Prompt enrichment
       llm_role => 'You are a financial chatbot named Penny',
       mission => 'Your mission is to assist your clients by providing financial education, account details, and basic information related to budgeting, saving, and different types of investments',
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and "GenWealth" company affiliation.',
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       additional_context => CONCAT(E'<BIO>', bio, E'</BIO>'),

       -- Add response restrictions
       response_restrictions => 'You are not a licensed financial advisor, so your must never provide financial advice under any circumstance. Always start your response by warning that you''re not authorized to provide financial advice. If you are asked for financial advice, politely decline to answer, and offer to help with financial education, account information, and basic information related to budgeting, saving, and types of investments.'
   )
   ```

1. Notice that we still greet Donya by name and mention that we know about her low risk tolerance, but we warn that we’re not giving financial advice.

   ![Guardrails](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/18-safeguards.png "Guardrails")

1. Adding response_restrictions improved the output, but it still relies on the model to implement the guardrail. Since we control the code for the llm() function, we can deterministically append a legal disclaimer to the end of every response to ensure any edge cases are covered. Take a look at the code for the llm() function to see how this is implemented.

   ```SQL
   -- Add a deterministic legal disclaimer
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 90
   )
   SELECT llm_prompt, llm_response, bio
   FROM profile, llm(
       -- User input
       prompt => 'I have $25250 to invest. What do you suggest?',

       -- Prompt enrichment
       llm_role => 'You are a financial chatbot named Penny',
       mission => 'Your mission is to assist your clients by providing financial education, account details, and basic information related to budgeting, saving, and different types of investments',
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and "GenWealth" company affiliation.',
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       additional_context => CONCAT(E'<BIO>', bio, E'</BIO>'),
       response_restrictions => 'You are not a licensed financial advisor, so your must never provide financial advice under any circumstance. Always start your response by warning that you''re not authorized to provide financial advice. If you are asked for financial advice, politely decline to answer, and offer to help with financial education, account information, and basic information related to budgeting, saving, and types of investments.',

       -- Add a deterministic legal disclaimer
       disclaimer => 'LEGAL DISCLAIMER: All output from this chatbot is provided for informational purposes only. It is not intended to provide (and should not be relied on for) tax, investment, legal, accounting or financial advice. You should consult your own licensed tax, investment, legal and accounting advisors before engaging in any transaction.'
   )
   ```

Congratulations! You’ve built three trustworthy Gen AI features using the data you already have and the skills you already know. You can either skip to the Clean Up step now, or you can complete the Challenge Lab below first.

## Challenge Lab

1. Take a closer look at the llm() function. You can run the query below again to view its definition (copy/paste it into a new query window for easier reading).

   ```SQL
   -- Show llm() function definition
   SELECT pg_get_functiondef(oid)
   FROM pg_proc
   WHERE proname = 'llm';
   ```

1. This is a custom function that was created specifically for this lab. Notice that it accepts several input parameters that we haven’t used yet. You can use these parameters to further tune and personalize your LLM output.

   ![LLM Function](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/genwealth/images/pgadmin/19-llm.png "LLM Function")

1. Experiment with different combinations of input parameters and notice the impact that spcific changes to the enriched prompt can produce. Here are a few examples to get you started.

   ```SQL
   -- Adjust runtime parameters for more creative or deterministic answers
   SELECT llm_prompt, llm_response
   FROM llm(
       prompt => 'I am a new investor. How should I get started?',
       temperature => 1.0, -- Controls the degree of randomness in token selection
       top_k => 40, -- Changes the number of tokens the model considers
       top_p => 1.0 -- Tokens are selected from the most to least probable until the sum of their probabilities equals the top-P
   );
   ```

   ```SQL
   -- Enable stock lookup functionality (highlights chained LLM calls and vector search)
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 1007
   )
   SELECT llm_prompt, llm_response, recommended_tickers, extractive_prompt, extractive_response FROM profile, llm(
       prompt => 'I just inherited $50,000 and want to invest it. What do you recommend?',
       llm_role => 'You are an experienced financial advisor named Penny.',
       mission => 'Your mission is to help your clients maximize their return on investment and outperform the general market.',
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name. Personalize your response to me, and tell me which of my specific personal details you used to answer my question.',
       max_output_tokens => 1024,
       enable_history => true,
       uid => id,
       enable_stock_lookup => true
   )
   ```

   ```SQL
   -- Ask for less aggressive options (highlights conversation history)
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 1007
   )
   SELECT llm_prompt, llm_response, recommended_tickers, extractive_prompt, extractive_response FROM profile, llm(
       prompt => 'Those options don''t look very good to me. What about some technology stocks?',
       llm_role => 'You are an experienced financial advisor named Penny.',
       mission => 'Your mission is to help your clients maximize their return on investment and outperform the general market.',
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name. Personalize your response to me, and tell me which of my specific personal details you used to answer my question.',
       max_output_tokens => 1024,
       enable_history => true,
       uid => id,
       enable_stock_lookup => true
   )
   ```

   ```SQL
   -- Set the output format to JSON
   WITH profile AS (
       SELECT *
       FROM user_profiles
       WHERE id = 1988
   )
   SELECT llm_prompt, llm_response, recommended_tickers, extractive_prompt, extractive_response FROM profile, llm(
       prompt => 'I just inherited $100,000 and want to invest it. What are a few stocks I should consider adding to my portfolio? I want to be aggressive.',
       llm_role => 'You are an experienced financial advisor named Penny.',
       mission => 'Your mission is to help your clients maximize their return on investment and outperform the general market.',
       user_role => CONCAT('My name is ', first_name, ' ', last_name, '. I am ', age, ' years old, and I have a ', risk_profile, ' risk tolerance.'),
       output_instructions => 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name. Personalize your response to me, and tell me which of my specific personal details you used to answer my question.',
       output_format => 'Format your response using JSON notation.',
       max_output_tokens => 1024,
       uid => id,
       enable_stock_lookup => true
   )
   ```

## Clean Up

Be sure to delete the resources you no longer need when you’re done with the lab and demo. If you created a new project for the lab as recommended, you can delete the whole project using the command below in your Cloud Shell session (NOT the pgadmin VM).

> DANGER: Be sure to set PROJECT_ID to the correct project, and run this command ONLY if you are SURE there is nothing in the project that you might still need.

```bash
# Set your project id
PROJECT_ID='YOUR PROJECT ID HERE'
gcloud projects delete ${PROJECT_ID}
```

## Summary

In this demo, you built new Gen AI features into your existing application using just SQL, including semantic search, customer segmentation, and a Gen AI chatbot. You also learned how to query your relational database using natural semantic query concepts.

If you'd like to see how this back end implementation could be leveraged on the front end, take a look at the [Front End Demo Walkthrough guide](./frontend-demo-walkthrough.md) to see GenWealth's Advisory Services UI in action.
