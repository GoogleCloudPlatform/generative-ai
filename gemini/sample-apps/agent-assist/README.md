# Agent Assist

## Introduction

Insurance agents often face challenges in managing their sales effectively, as they struggle to keep track of their clients, maintain communication, and organize their sales efforts efficiently. Without proper tools, they find it difficult to stay on top of their tasks and engage with potential and existing customers in a timely manner. Moreover, the lack of automated processes leads to wasted time on administrative tasks, hindering their productivity and ultimately affecting their sales performance.

The aim of this product is to provide insurance agents with an easy-to-access knowledge base of information about insurance policies, products, and services. Agents can use Enterprise Search to quickly search for and retrieve information about insurance products and services to answer customer queries. The capabilities can also be extended to analyze customer data and provide insights to agents about customer behavior and preferences, for a more personalized customer experience.

## App Overview

### Interface

<center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image.png" width="50%" alt="Introduction Page"></center>

### Components

1. ### Chatbot

   The first and the main component is the multi-agent chatbot which has been designed to aid Insurance Agents. The chatbot leverages the power of GenAI to perform a variety of actions.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-1.png" width="50%" alt="Chatbot Workflow"></center>

   The main tasks that the chatbot performs are as follows:

   - **Policy Search** The chatbot can answer questions related to the coverages in a single policy, questions like comparing two policies for a particular metric or even questions like recommending the best policy under some given constraints.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-2.png" width="50%" alt="Policy Search Example"></center>

   - **Mailing** The chatbot can be directly used to send emails to customer. The chatbot uses the reasoning capabilities of the latest Gemini model to generate customised emails for the customers, and is also trained to pickup context from earlier conversations.

   - **Calendar Events** The chatbot can be used to schedule meets with customers as well as to get the list of upcoming appointments, making it easier for an agent to stay updated on the go.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-5.png" width="50%" alt="Calendar Events Setting"></center>
   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-4.png" width="50%" alt="Calendar Events Showing"></center>

   - **Crafting Sales Pitches**: The chatbot can also be used to generate sales pitches for policies. Behind the hood, the chatbot leverages LLMs to generate a sales pitch focussing on key aspects of the Insurance Policy.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-6.png" width="50%" alt="Creating Sales Pitch"> </center>

   The code for the chatbot can be found in [backend/src/chatbot](backend/src/chatbot) directory. A separate file for each agent [search](backend/src/chatbot/agents/search_agent), [sales_pitch](backend/src/chatbot/agents/sales_pitch.py), [calendar](backend/src/chatbot/agents/calendar.py), [email](backend/src/chatbot/agents/mail.py), [fallback](backend/src/chatbot/agents/fallback_component.py) can be found inside the [backend/src/chatbot/agents](backend/src/chatbot/agents) directory.

   <br/>

   > **Working of the chatbot** The chatbot relies on the multi-step reasoning capabilities of the latest Gemini family of models. The input query goes into the `orchestration_engine` which leverages `Gemini` to detect the intent and calls the desired agent based on the query. `Gemini` itself extracts the required parameters to be pased to each agent from the user query, taking help of the `chat_history` wherever necessary. Each agent in turn makes use of `Gemini` and the respective `API` to perform the desired action.

2. ### Dashboard

   Agent-Assist offers a user-friendly dashboard that provides agents with real-time insights into their sales performance and an at-a-glance view of key performance indicators (KPIs) relevant to an insurance agent's activity.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-7.png" width="50%" alt="Dashboard Page 1"></center>

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-8.png" width="50%" alt="Dashboard Page 2"></center>

   The code for the dashboard can be found in the [backend/src/apis](backend/src/apis) folder

3. ### Workbench

   Agent-Assist offers a versatile workbench where agents can manage their current clients and prospects seamlessly. Key features of the workbench include: Communication tools, Client database, a kanban board.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-9.png" width="50%" alt="Workbench Page"></center>

   - **The contacted customer’s** details which shows up like a pop up when clicked on the customer’s title in the table. It also has the summary of most recent conversation summary with the customer, an option to mail them after generating the mail content there itself and an option to set up a follow up meeting

   - **The potential customer’s** details which shows up like a pop up when clicked on the customer’s title in the table. It has an option to mail the customer a sales pitch after generating the sales pitch there itself.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-11.png" width="50%" alt="Contacted and Potential customers"></center>

   - **A kanban board** that categorizes the customers based on the 5 categories listed in the page. The agent can drag and drop the customer’s tiles from one box to another and the backend will be updated simultaneously.

   <center><img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/agent-assist/readme-images/image-10.png" width="50%" alt="Kanban Board"></center>

   The files for these can again be found in the [backend/src/apis](backend/src/apis) folder

   <br/>

   > `Gemini` is again used to generate content like Email and Sales Pitch.
