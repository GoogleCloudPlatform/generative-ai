# AI-Powered Market Analyst

> A multi-agent system that leverages LLMs to research companies and industries, generate tailored AI use cases, and provide implementation resources. Built with LangChain and LangGraph for intelligent workflow orchestration.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org)

## Features

- **🔍 Intelligent Research**: Automated company and industry analysis using web search
- **🎯 AI Use Case Generation**: Tailored AI/ML strategies with business value assessment  
- **📚 Resource Discovery**: Find datasets and tools from Kaggle, HuggingFace, and GitHub
- **🤖 Multi-Agent System**: Coordinated agents using LangGraph orchestration
- **🌐 Full-Stack App**: FastAPI backend with Next.js frontend

## Quick Start

### Prerequisites

- Python 3.10+, Node.js 18+
- API keys: [Google Gemini](https://aistudio.google.com/app/apikey), [SERP API](https://serpapi.com/)

### Installation

```bash
# Clone the repository
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd generative-ai/gemini/agents/market-research-agent

# Backend setup
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup  
cd ../frontend
npm install
```

### Configuration

Create `.env` file in backend/:
```env
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Optional Langfuse Monitoring
LANGFUSE_PUBLIC_KEY=pk-lf-your_langfuse_public_key
LANGFUSE_SECRET_KEY=sk-lf-your_langfuse_secret_key

# LLM Configuration
LLM_PROVIDER=llm_provider # e.g., "gemini"
LLM_MODEL=llm_model # e.g., "gemini-2.5-pro-preview-03-25"
```

Create `.env.local` in frontend/:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run the Application

```bash
# Start backend (from backend/)
uvicorn app:app --port 8000 --reload

# Start frontend (from frontend/)
npm run dev
```

Visit `http://localhost:3000` to use the application.

## How It Works

![Workflow](https://github.com/user-attachments/assets/940f3973-5b36-4af9-bc39-f501c53afc32)

1. **Research Agent** - Gathers company/industry information
2. **Use Case Agent** - Generates AI implementation strategies  
3. **Resource Agent** - Discovers relevant datasets and tools
4. **Orchestrator** - Coordinates the multi-agent workflow

## Project Structure

```bash
market-research-agent
│
├── backend                       ; Core backend services
│   ├── config
│   │   ├── settings.py           ; Environment and API configuration
│   │   └── logging_config.py     ; Centralized logging setup
│   ├── agents                    ; Specialized AI agents
│   │   ├── industry_research_agent.py
│   │   ├── use_case_generation_agent.py
│   │   ├── resource_collection_agent.py
│   │   └── orchestrator.py       ; Multi-agent coordination
│   ├── tools                     ; External service integrations
│   │   ├── search_tools.py       ; Web search capabilities
│   │   ├── dataset_tools.py      ; Dataset discovery and analysis
│   │   ├── analysis_tools.py     ; Business analysis utilities
│   │   └── document_tools.py     ; Document processing
│   ├── models                    ; LLM interface abstraction
│   │   ├── llm_interface.py      ; Generic LLM interface
│   │   └── gemini_client.py      ; Google Gemini integration
│   ├── workflows                 ; Orchestrated analysis workflows
│   │   ├── research_workflow.py
│   │   ├── use_case_workflow.py
│   │   └── resource_workflow.py
│   └── app.py                    ; FastAPI application server
│
├── frontend                      ; Next.js web application
│   ├── src
│   │   ├── components
│   │   │   ├── layout           ; Application layout components
│   │   │   ├── ui               ; Reusable UI components
│   │   │   ├── forms            ; Input and form components
│   │   │   └── results          ; Analysis result displays
│   │   ├── pages                ; Next.js page routing
│   │   ├── services             ; API integration services
│   │   └── styles               ; Application styling
│   └── package.json
│
└── credentials                  ; API keys and credentials (gitignored)
```

## Usage

1. Enter company name (e.g., "Microsoft") or industry (e.g., "Technology")  
   - For company analysis, use a specific company name
   - For industry analysis, use a broader term like "Healthcare" or "Finance"
2. Set number of AI use cases to generate
3. Wait for analysis completion  
4. Review generated use cases and resources
5. Download markdown report

## API Endpoints

- `POST /api/analyze` - Start analysis
- `GET /api/analysis/{id}` - Get results  
- `GET /api/markdown/{id}` - Download report
- `GET /health` - Health check

## Tech Stack

**Backend**: FastAPI, LangChain, LangGraph, Google Gemini  
**Frontend**: Next.js, React, Tailwind CSS  
**Integrations**: SERP API, Kaggle API, HuggingFace API

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Examples

**Company Analysis**: Analyze "Tesla" to get AI use cases for automotive industry  
**Industry Analysis**: Research "Healthcare" to discover AI opportunities in medical sector

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- [Google Gemini](https://ai.google.dev/) for language model capabilities

---

**Disclaimer**: This is not an officially supported Google product. The code in this repository is for demonstrative purposes only.