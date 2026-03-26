# 🐶 Meet PromptWatchDog: Bringing NLP to Real-Time System Monitoring with Gemini

Monitoring modern applications can feel like reading tea leaves. Traditional metrics tell you *how much* traffic you have or *how many* errors occurred, but they rarely tell you *what* those errors mean without tedious, rigid regex queries or custom code.

What if you could track application data using plain English? What if you could say, "Alert me if the sentiment of this message stream turns negative," or "Track how many times customers mention our competitor's new feature," and have it *just work*—without redeploying code?

Enter **PromptWatchDog**—a serverless, event-driven framework that leverages generative AI to turn unstructured data streams into structured metrics in real-time.

<div align="center">
  <img src="/Users/emarco/GithubProjects/PromptWatchDog/static/dashboard.png" width="48%" alt="Dashboard" />
  <img src="/Users/emarco/GithubProjects/PromptWatchDog/static/metric_explorer.png" width="48%" alt="Metrics Explorer" />
</div>

---

## 💡 The Problem: Why Traditional Metrics Fail

Imagine you run an E-commerce platform. You have standard metrics for CPU load, HTTP 500s, and DB latency. But suddenly, your support team is swamped. You look at the logs, but it's a sea of text. 

Traditional metrics can't tell you that 50 users in the last 10 minutes are complaining about a **"payment loop bug on iOS 17"**. 

Regex can help, but it's brittle. What if they say "can't pay," "checkout broken," or "apple pay spinning"? You can't write regex for every variation of human speech.

### The Solution: Natural Language Metrics

PromptWatchDog flips this paradigm. It uses **Google Gemini** as an intelligent evaluation engine. You define what you want to track using a natural language prompt, and PromptWatchDog watches the stream, evaluates every message, and emits structured logs.

---

## 🔍 A Specific Example: The "Shipping Panic" Detector

Let's look at a super specific scenario. You are launching a big sale, and you want to know *immediately* if there is a logistics breakdown.

Instead of writing code to parse chat logs for keywords, you go to your PromptWatchDog Dashboard and create a new prompt:

> **Watchdog Name**: Shipping Panic Detector
> **Prompt**: 
> "You are a logistics monitor. Evaluate if the following customer message indicates a panic or severe frustration regarding shipping delays, lost packages, or broken delivery promises. If they are just asking for a tracking number, that is NOT a panic.
> Message: {text}"

### The Magic: Real-Time Transformation

When a user messages: *"I ordered this 3 days ago for a birthday today and it still says processing! This is ridiculous, I need a refund now!"*

PromptWatchDog intercepts this via Pub/Sub, runs it through Gemini (via LangChain), and outputs this structured JSON:

```json
{
  "event": "watchdog_evaluation",
  "watchdog_id": "ship_panic_001",
  "watchdog_name": "Shipping Panic Detector",
  "matched": true,
  "reasoning": "The user is expressing severe frustration ('ridiculous', 'need a refund now') about a shipping delay ('still says processing' after 3 days) for a time-sensitive event (birthday).",
  "message_id": "msg_994"
}
```

This JSON is picked up by Google Cloud Logging, which automatically increments a **Log-Based Metric**. 📈

---

## 🏗️ The Architecture

![PromptWatchDog Architecture Diagram](/Users/emarco/GithubProjects/PromptWatchDog/static/architecture.png)
*High-level architecture of PromptWatchDog.*

Here is how the data flows from a user message to a live dashboard:

```mermaid
graph TD
    User[User Message] -->|Publishes| PubSub[Cloud Pub/Sub Topic: `messages`]
    PubSub -->|Triggers| CloudRun[Cloud Run/Function]
    
    subgraph "The Brain (LangChain Orchestrator)"
        CloudRun -->|Fetch active prompts| Firestore[(Firestore)]
        Firestore -->|Return Prompts| CloudRun
        CloudRun -->|Send Message + Prompt| Gemini[Gemini Pro (Vertex AI)]
        Gemini -->|Structured Output| CloudRun
        CloudRun -->|Trace Chain| LangSmith[LangSmith]
    end

    CloudRun -->|Write Structured JSON| CloudLogging[Cloud Logging]
    CloudLogging -->|Parse Labels| LogMetric[Log-Based Metric]
    LogMetric -->|Visualize| Dashboard[GCP Metrics Explorer]
```

---

## 🛠️ The Tech Stack Detail

### 🧠 The Intelligence Layer
*   **Gemini 3.5 Flash Lite**: The core brain. It’s fast enough for real-time streaming and smart enough to handle complex reasoning.
*   **LangChain**: The orchestrator. We use `PromptTemplate` to inject variables and `with_structured_output` to force Gemini to return strict Pydantic models.

### 🔍 Tracing and Observability (The Secret Sauce!)
*   **LangSmith for Tracing**: Operating LLMs in production can be opaque. By integrating **LangChain + LangSmith**, we get deep visibility. We can trace exactly how prompts are interpreted, monitor latency, track token usage, and identify where the chain might be failing or slow. It’s essential for debugging fine-grained prompt logic without guessing!

### 🏗️ The Infrastructure (Google Cloud)
*   **Pub/Sub**: The event bus.
*   **Firestore**: The dynamic database for prompts.
*   **Cloud Logging**: The sink for structured data.
*   **Metrics Explorer**: The visualization engine.

---

## 📸 See It In Action

### 1. Creating a Prompt Locally
You use the local Next.js Dashboard to manage your prompts without exposing admin rights to the cloud.

![Creating a Prompt](/Users/emarco/GithubProjects/PromptWatchDog/static/create-prompt.png)
*Managing prompts locally follows the Principle of Least Privilege.*

---

## 🎯 Summary

PromptWatchDog bridges the gap between raw, unstructured log data and rich, business-level insights. It allows teams to move fast, add monitoring dimensions on the fly, and use the power of Gemini to understand *intent* rather than just *keywords*.

Are you ready to stop parsing logs and start *asking* them what they mean? 🐶

***

### 👤 Author
**Eden Marco** - *LLM Specialist @ Google Cloud*
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/eden-marco/)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://twitter.com/EdenEmarco177)
