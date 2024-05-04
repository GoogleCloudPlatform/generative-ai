# Cymbal Bank Website Demo: CymBuddy and Search

This codebase showcases the Cymbal Bank demo website, featuring CymBuddy, a personalized assistant built with Dialogflow CX and Gemini Pro. The website and CymBuddy also leverage Retrieval Augmented Generation (RAG) to provide accurate and relevant search results across Cymbal Bank's range of products and services.

## **Main Features:**

- **Multilingual Support:** The website is available in English, Hindi, and Kannada, ensuring accessibility for a wider audience.
- **AI-powered Chatbot:** Interact with our intelligent chatbot available in both English and Hindi for assistance with account inquiries, financial planning, and more.
- **Personalized User Experiences:** We offer tailored experiences for three distinct personas:
- **Affluent Persona (Ayushi):** Focused on investment opportunities, wealth management, and travel benefits.
- **Mid-Tier Persona (Ishan):** Balancing expenses, exploring investment options, and building financial stability.
- **Gen Z Persona (Chulbul):** Budgeting tools, savings goals, and personalized recommendations for achieving financial independence.
- **Financial Management Tools:** Gain insights into your spending habits, track investments, set financial goals, and explore various financial products.
- **Investment Options:** Access a range of investment options including Fixed Deposits (FDs), Mutual Funds (both equity and debt), and Systematic Transfer Plans (STPs).
- **Additional Services:**
- **Overdraft Facility:** Get quick access to funds when needed.
- **Travel Insurance:** Enjoy complimentary travel insurance for your trips.
- **Personalized Recommendations:** Receive tailored suggestions for events, entertainment, and other activities based on your interests.

## **How to Use the Demo:**

1. **Access the demo website and select your preferred language**

   - English: <https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/>
   - Hindi: <https://cymbalbankhi-n3zk63yvta-uc.a.run.app/>

   **NOTE:** Website is available in English, Hindi and Kannada and the chatbot is supported in English and Hindi.

   ![Website Homepage](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/cymbal_bank_homepage.png)

2. **Login using the provided user details for the persona you wish to explore and Interact with the chatbot** using natural language to explore features and functionalities. **Review the investment summaries, market outlook, and personalized recommendations.**

   - **Affluent Persona (Ayushi):** Focused on investment opportunities, wealth management, and travel benefits.\
     Username: <ayushisharma.cb@gmail.com>\
     Password: 123456.cb\
     [Sample Chat](files/sample_chat_scripts/affluent_persona_ayushi.md)
   - **Mid-Tier Persona (Ishan):** Balancing expenses, exploring investment options, and building financial stability.\
     Username: <ishanjoshi.cb@gmail.com>\
     Password: 123456.cb\
     [Sample Chat](files/sample_chat_scripts/midtier_persona_ishan.md)
   - **Gen Z Persona (Chulbul):** Budgeting tools, savings goals, and personalized recommendations for achieving financial independence.\
     Username: <pandeychulbul.cb@gmail.com>\
     Password: 123456.cb\
     [Sample Chat](files/sample_chat_scripts/genz_persona_chulbul.md)

   ![Login](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/cymbal_bank_login.png)

3. **Interact with the RAG powered Search functionality to get information about Cymbal Bank products and services**

   ![Search](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/cymbal_bank_search.png)

## **Additional Information:**

- The demo showcases the core functionalities and capabilities of CymBuddy and the Cymbal Bank platform.
- The investment data and recommendations are simulated and for illustrative purposes only.
- This repository is intended for demonstration purposes. The final product may include additional functionality.
  
  For example, this demo does not support actual transactions while creating FDs or STPs; it only modifies database entries to simulate them. A fintech/bank adopting this demo, would need to add transaction support.
  