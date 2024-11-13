# Attacks and Mitigation Labs

These comprehensive learning notebooks dive deep into the critical world of LLM security, equipping you with the knowledge and skills to build, deploy, and maintain secure and trustworthy AI solutions. From understanding the latest attack vectors to implementing cutting-edge defenses, these notebooks are your guide to navigating the evolving landscape of LLM security.

- [Responsible AI with Gemini API in Vertex AI: Safety ratings and thresholds](gemini_safety_ratings.ipynb)

  - Call the Gemini API in Vertex AI and inspect safety ratings of the responses
  - Define a threshold for filtering safety ratings according to your needs

- [LLM Prompt attacks and mitigation](gemini_prompt_attacks_mitigation_examples.ipynb)

  - Simple prompt design prompt design
  - Antipatterns on prompt design with PII data and secrets
  - Prompt Attacks:
    - Data Leaking
    - Data Leaking with Transformations
    - Modifying the Output (Jailbreaking)
    - Hallucinations
    - Payload Splitting
    - Virtualization
    - Obfuscation
    - Multimodal Attacks (Image, PDF & Video)
    - Model poisoning
  - Protections & Mitigation with:
    - Data Loss Prevention
    - Natural Language API (Category Check, Sentiment Analysis)
    - Malware checking
    - LLM validation (Hypothesis Validation, DARE, Strict Input Validation with Random Token)
    - Responsible AI Safety filters
    - Embeddings

- [ReAct and RAG attacks and mitigation options](react_rag_attacks_mitigations_examples.ipynb)

  - Simple ReAct application design
  - Attacks using ReAct Agent
  - Mitigation using ReAct Agent information
  - Simple RAG application
  - Attacks and mitigation for RAG applications
