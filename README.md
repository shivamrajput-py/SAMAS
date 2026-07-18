<div align="center">
  
#  SAMAS (Strategic Agentic Matching & Assessment System)

An Enterprise-Grade, Autonomous AI Multi-Agent Pipeline that revolutionizes the job search process by deeply understanding your technical profile, assessing your skills through an interactive AI interview, and autonomously hunting, filtering, and hybrid-matching you with the perfect jobs.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=for-the-badge&logo=pinecone&logoColor=white)](https://www.pinecone.io/)
[![LangSmith](https://img.shields.io/badge/LangSmith-000000?style=for-the-badge)](https://smith.langchain.com/)

</div>

---

##  Overview

**SAMAS** is not just another job board scraper. It is a highly sophisticated, multi-agent LLM orchestration system built with **LangGraph** that acts as a personal technical recruiter. It guarantees precision, eliminates AI hallucinations via strict guardrails, and optimizes token costs using a sophisticated filtering funnel.

###  Key Features
- **Intelligent Resume Parsing (PRISM):** Extracts dense skill matrices and career timelines from raw PDFs. Protected by **Guardrails AI** to strictly enforce JSON schemas and prevent prompt injections.
- **Dynamic AI Interview (LUCID):** An LLM-as-a-judge system dynamically generates technical questions based *strictly* on your claimed skills, evaluating your answers to adjust your confidence vector.
- **Autonomous Job Sweeper (RADAR):** Spawns asynchronous, parallel workers to scrape global job boards (via SerpAPI) based on multi-query strategies.
- **Deep Analyst (CIPHER):** Employs **Local BM25 Pre-filtering** to instantly drop the bottom 25% of irrelevant jobs (saving LLM tokens), detects "ghost jobs", and extracts structured JD requirements.
- **Hybrid Matching Engine (KAIROS):** Embeds both your profile and the JDs into **Pinecone** using Dense Vectors (Semantic meaning via OpenAI) and Sparse Vectors (Exact Keyword matches via BM25/SPLADE). Performs an `alpha=0.5` balanced hybrid search for pinpoint accuracy.
- **Enterprise Observability:** Fully instrumented with **LangSmith** for real-time tracing of agent reasoning, latency, and token consumption.
- **CI/CD Evaluations:** Unit tested with **DeepEval** to programmatically score LLM Faithfulness and Answer Relevancy.

---

##  Agentic Architecture

The system utilizes a directed acyclic graph (DAG) via **LangGraph** to orchestrate five distinct autonomous agents.

```mermaid
graph TD
    User([User Uploads Resume]) --> PRISM
    
    subgraph Phase 1: Ingestion & Assessment
        PRISM[PRISM Agent<br/>Resume Extraction] --> LUCID
        LUCID[LUCID Agent<br/>Interactive Tech Interview]
    end
    
    LUCID --> |Adjusts Skill Vectors| RADAR
    
    subgraph Phase 2: Autonomous Hunt
        RADAR[RADAR Agent<br/>Global Job Sweep] --> CIPHER
        CIPHER[CIPHER Agent<br/>BM25 Pre-filter & JD Analysis]
    end
    
    CIPHER --> KAIROS
    
    subgraph Phase 3: Hybrid Resolution
        KAIROS[KAIROS Agent<br/>Pinecone Hybrid Search] --> Output([Final Curated Job Matches])
    end

    %% Architecture Details
    classDef agent fill:#1e1e2e,stroke:#89b4fa,stroke-width:2px,color:#cdd6f4;
    class PRISM,LUCID,RADAR,CIPHER,KAIROS agent;
```

### The Filtering Funnel Strategy
SAMAS is explicitly engineered to balance **High Precision** with **Low API Cost**.
1. **Raw Scraping:** Grabs 100+ jobs via SerpAPI.
2. **Deep Deduplication (Free):** Exact title/company hashing.
3. **BM25 Pre-filtering (Free):** CPU-bound `rank-bm25` drops the bottom 25% of jobs instantly.
4. **LLM Extraction (Expensive):** Only the highest potential jobs are sent to the LLM for deep analysis.
5. **Pinecone Hybrid Search (Fast):** Resolves the final top 5 matches combining semantic meaning and keyword necessity.

---

##  Tech Stack

### Frontend
- **Framework:** Next.js (React 18)
- **Styling:** CSS Modules, Modern Glassmorphism UI
- **Real-time Comms:** Server-Sent Events (SSE) for live terminal-style streaming of agent reasoning.

### Backend & AI
- **API Framework:** FastAPI, Uvicorn, Python 3.12+
- **Agent Orchestration:** LangChain, LangGraph
- **LLM Gateway:** OpenRouter, LiteLLM (Supports DeepSeek, OpenAI, Anthropic)
- **Vector Database:** Pinecone (with `pinecone-text` for Sparse BM25 Vectors)
- **Keyword Search:** `rank-bm25`
- **Scraping:** SerpAPI

### Enterprise & MLOps
- **JSON Security:** Guardrails AI (`Guard.from_pydantic()`)
- **Observability & Tracing:** LangSmith
- **LLM Evaluations:** DeepEval (FaithfulnessMetric, AnswerRelevancyMetric)
- **Testing:** Pytest

---

##  Local Setup & Installation

### Prerequisites
You will need API keys for:
- [OpenRouter](https://openrouter.ai/) (or OpenAI/Anthropic)
- [Pinecone](https://www.pinecone.io/)
- [LangSmith](https://smith.langchain.com/)
- [SerpAPI](https://serpapi.com/)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/samas.git
cd samas
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
OPENROUTER_API_KEY=your_key_here
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=samas-index
SERPAPI_API_KEY=your_serpapi_key

# LangSmith Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=SAMAS-Production
```

Run the backend server:
```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory (Optional since Next.js rewrites handle this):
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Run the frontend server:
```bash
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

##  Running LLM Evaluations

To verify the mathematical accuracy of the agents without hallucination, run the DeepEval test suite:
```bash
cd backend
pytest tests/test_evals.py
```
*(Note: Requires `OPENAI_API_KEY` to be set in `.env` as DeepEval uses GPT-4 as the judge model).*

---

##  Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

##  License
This project is licensed under the MIT License.
