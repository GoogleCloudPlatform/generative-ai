# 🚀 Gemini Enterprise Migration Agent

> Seamlessly migrate your low-code agents and Custom Instructions (Gems) to Gemini Enterprise.

Built with the **Agent Development Kit (ADK)**, this specialized AI agent facilitates the migration of low code agents and notebooklm from one Gemini Enterprise App to another and from Google Workspace Gems to Gemini Enterprise app. It can be further extended to supports migration of 3rd Party agents to Gemini Enterprise App via adapters(mappings between 3rd party agent and import format required by Gemini Enterprise App)

## Architecture

The following diagram illustrates the high-level architecture of the migration agent and its interactions with various services.

![Architecture Diagram](./ge-migration-agent-architecture.png)

## 🛠️ Capabilities & Skills

### 🤖 Agent Migration
- **Discovery**: List and explore source low-code agents available for migration.
- **Direct Migration**: Seamlessly transfer agent definitions to target Gemini Enterprise engines.
- **GCS Staging**: Export definitions to Google Cloud Storage for isolated or staged migrations.

### 💎 Gem Migration
- **Gem Processing**: Extract Custom Instructions (Gems) from HTML dumps(takeout), mapping descriptions and file references.

### 📚 Notebooklm migration
- **Instant Notebooks**: Create NotebookLM-style knowledge bases in the target project.
- **Batch Ingestion**: Rapidly populate notebooks with sources from web URLs.

### 🛡️ Validation & Safety
- **Pre-flight Checks**: Verify target environment supports required connectors (Gmail, Drive, Search).
- **Smart Alerts**: Get detailed reports and interactive prompts for missing dependencies.
- **Safe Guardrails**: Enforce explicit Project and Engine IDs to prevent accidental data overwrites.

## 🚀 Getting Started

### 📋 Prerequisites
- **Python**: Version 3.10 or higher.
- **Google Cloud**: A project with the **Discovery Engine API** enabled.
- **Authentication**: Application Default Credentials (ADC) configured.

### 🛠️ Setup & Run

1. **Configure Environment**: Ensure your GCP project is set up and Application Default Credentials (ADC) are configured. Make sure your `.env` file matches the format in `ge_migration_agent/.env.sample`.
2. **Option A: Run the Deterministic CLI (Highly Recommended)**:
   For 100% reliable, fast, and deterministic execution of migrations without any AI dependencies, use the newly added root entrypoint script:
   ```bash
   # Show help and all available commands
   ./migrate.py --help

   # List notebooks in the source project
   ./migrate.py list-notebooks

   # Migrate an entire notebook and all of its sources atomically
   ./migrate.py migrate-notebook "my-notebook-title" --source-project 12345 --target-project 67890
   ```
3. **Option B: Run the Conversational AI Agent**:
   For natural language guidance and conversational interactions, launch the ADK playground:
   ```bash
   ./ge_migration_agent/run_web_playground.sh
   ```
   Open `http://localhost:8001` in your browser to chat with the agent. The agent is now powered by the exact same underlying deterministic core.


## 💡 Example Usage

Here is a sample session showing how to migrate a batch of Gems:


### Sample Session Traces

Here are some actual prompts and responses from a migration session:

**User**: 
> help
> 
**Agent**: 
> Hello! I can help you migrate notebooks or manage employee-made agents.

To get started, please provide the following details for your source environment:

Project Number
Project ID
Region
Engine ID
And for your target environment:

Project Number
Project ID
Region
Target Engine ID
Once I have these, I can assist you with tasks such as:

Listing notebooks
Migrating notebooks
Listing employee-made agents
Migrating employee-made agents
Exporting agents to GCS
Importing agents from GCS
Creating agents from Gem instructions
Importing multiple Gems from a file

**User**: (Provides project details)
> source project number <SOURCE_PROJECT_NUMBER>, project id <SOURCE_PROJECT_ID> , region global , engine id <SOURCE_ENGINE_ID> target project number <TARGET_PROJECT_NUMBER> , project id <TARGET_PROJECT_ID> , region global, Target engine id is <TARGET_ENGINE_ID>

**Agent**:
> Thank you for providing the source and target environment details! I have stored them. ... What would you like to do next?

**User**:
> List all the human made agents in source

**Agent**:
> I found the following employee-made agents in your source environment: ...
> 
| Display Name | Description |
| :--- | :--- |
| Email Strategists | Agent to help interact with your emails. |
| Summarize Daily Emails | Retrieves and summarizes emails received within the last 24 hours. |
| Daily Email Summarizer | Retrieves and summarizes emails from the past 24 hours. |
| Schedule Meeting | Schedules a meeting on the calendar based on user input. |
| `QBR` Generator | A central orchestration agent designed to generate comprehensive Quarterly Business Reviews (`QBRs`) by coordinating specialized data retrieval from sub-agents. It analyzes user requests, delegates to finance and sentiment experts, and synthesizes final reports. |
| AI Informant Orchestrator | Orchestrates information gathering from various specialized agents and synthesizes the results into a comprehensive report. |
| Google Stock Price Finder | Searches for and displays today's Google stock price. |

....
....
....

**User**:
> Migrate `QBR` Generator from source to target

**Agent**:
> The agent '`QBR` Generator' has been successfully migrated to your target environment.
> WARNING: Some connectors were ignored: ['Monday Mcp', 'Ge Gmail', ...]

**User**:
> List all the notebooks along with name, source type, source, url.
> 
**Agent**:
> I have retrieved the following notebooks and their sources:

| Notebook Name | Source Title | Source URL |
| :--- | :--- | :--- |
| ge  | 4 ways Gemini Enterprise makes work easier for everyone - Google Blog | [Link](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/4-ways-gemini-enterprise-makes-work-easier-for-everyone/) |
| ge  | Gemini Enterprise AI: Features, Use Cases & How It Helps Businesses | [Link](https://advantailabs.com/blog/google-gemini-enterprise-your-shortcut-to-effortless-productivity) |
....
....
....

**User**:
> Migrate the notebook named ge to target

**Agent**:
> The notebook "ge" and all its sources have been successfully migrated to the target environment.

**User**:
> Please import the Gems from the file /usr/local/google/home/ntuteja/ge-migration-agent/gemini_gems_data.html in Target

**Agent**:
> The Gems from the file /usr/local/google/home/ntuteja/ge-migration-agent/gemini_gems_data.html have been successfully imported to your target environment.

## Project Structure
- `ge_migration_agent/`: Contains the agent definition, tools, and execution scripts.
  - `agent.py`: Core agent definition and tool implementations.
  - `run_web_playground.sh`: Script to start the ADK web server.
- `gemini_gems_data.html`: Sample data file for batch Gems import.
