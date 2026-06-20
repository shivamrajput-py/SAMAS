# SAMAS â€” Multi-Agent AI Job Intelligence System

## The Vision

SAMAS is a **multi-agent AI system** that acts as a brutally honest career advisor. Unlike existing tools that blindly trust self-reported resumes and do keyword matching, SAMAS:

1. **Interrogates** the user through a structured conversational loop to build a proof-scored skill profile
2. **Searches** across multiple job platforms with semantic depth â€” not just titles, but full JD analysis
3. **Matches** jobs using embedding-based similarity against verified skills
4. **Classifies** jobs into 3 tiers: Easy Gets, Best Matches, and Stretch Goals
5. **Detects** ghost jobs and scams before the user wastes time applying
6. **Generates** tailored resumes per job and skill gap roadmaps on demand

---

## What You'll Learn (The CV Gold)

This project is deliberately designed to teach you production-grade AI engineering. Here's the concept map:

| Concept | Where You'll Learn It |
|---|---|
| **LangGraph StateGraph** | Core orchestration â€” every agent is a graph node |
| **Human-in-the-Loop (HITL)** | Interview Agent pauses graph, waits for user input, resumes |
| **Cross-Session Persistent Memory** | PostgreSQL checkpointing â€” user can close browser, come back next day |
| **Streaming (SSE/WebSocket)** | Real-time token streaming from agents to React frontend |
| **Production RAG** | Hybrid BM25 + vector search for JDâ†”Profile matching |
| **Multi-Agent Orchestration** | Supervisor pattern routing between 6 specialized agents |
| **Tool Use in Agents** | Agents calling APIs (SerpAPI, GitHub, Adzuna) as LangGraph tool nodes |
| **Prompt Engineering** | Structured extraction, scoring rubrics, few-shot evaluation |
| **Cost Management** | LiteLLM proxy for model routing + token tracking |
| **Evaluation & Testing** | LangSmith tracing for agent trajectories + pytest |
| **Async Background Jobs** | Celery/Redis for JD deep-parsing while user continues chatting |
| **Vector Databases** | ChromaDB for embedding JDs and user profiles |
| **API Design** | FastAPI with proper REST + SSE endpoints |

---

## System Architecture

```mermaid
graph TB
    subgraph "Frontend â€” React + Vite"
        UI["Chat UI + Dashboard"]
    end

    subgraph "API Layer â€” FastAPI"
        API["REST + SSE Endpoints"]
        WS["WebSocket Handler"]
    end

    subgraph "Orchestration â€” LangGraph"
        SUP["ðŸŽ¯ Supervisor Agent"]
        PA["ðŸ“„ Profile Builder Agent"]
        IA["ðŸŽ¤ Interview Agent"]
        JS["ðŸ” Job Search Agent"]
        JA["ðŸ“Š JD Analyzer Agent"]
        MA["âš–ï¸ Matching & Ranking Agent"]
        OA["ðŸ“‹ Output Agent"]
    end

    subgraph "Tool Nodes"
        T1["PDF Parser (pdfplumber)"]
        T2["GitHub API"]
        T3["SerpAPI (Google Jobs)"]
        T4["Adzuna API"]
        T5["Jooble API"]
        T6["Remotive API"]
    end

    subgraph "Data Layer"
        PG["PostgreSQL (Checkpoints + User Data)"]
        CH["ChromaDB (JD + Profile Embeddings)"]
        RD["Redis (Session Cache + Task Queue)"]
    end

    subgraph "Infrastructure"
        LL["LiteLLM Proxy (Cost Management)"]
        LS["LangSmith (Tracing)"]
    end

    UI --> API
    UI --> WS
    API --> SUP
    WS --> SUP
    SUP --> PA
    SUP --> IA
    SUP --> JS
    SUP --> JA
    SUP --> MA
    SUP --> OA
    PA --> T1
    PA --> T2
    JS --> T3
    JS --> T4
    JS --> T5
    JS --> T6
    JA --> CH
    MA --> CH
    SUP --> PG
    SUP --> LL
    LL --> LS
```

---

## Agent Architecture (Deep Dive)

### Agent 1: Profile Builder Agent

**What it does:** Extracts structured information from the user's resume PDF and any linked profiles.

**What you'll learn:**
- PDF text extraction with `pdfplumber` (handling tables, columns, bad formatting)
- LLM-based structured data extraction using Pydantic output schemas
- GitHub API integration (commits, languages, contribution patterns)
- Designing a formal schema for skill representation

**How it works:**
1. User uploads resume PDF â†’ `pdfplumber` extracts raw text
2. LLM call with structured output â†’ extracts into `UserProfile` Pydantic schema
3. If GitHub URL found â†’ calls GitHub API to get language distribution, commit frequency, repo quality
4. Outputs a structured profile with initial proof scores (0.0-1.0 scale)

**Proof Score Model:**
```
proof_score = weighted_average(
    resume_mention    Ã— 0.2,  # Mentioned in resume (baseline)
    experience_years  Ã— 0.2,  # Years of stated experience
    project_evidence  Ã— 0.25, # Mentioned in project descriptions
    github_evidence   Ã— 0.2,  # Found in GitHub repos
    certification     Ã— 0.15  # Has relevant certification
)
```

> [!IMPORTANT]
> The proof score is a **heuristic**, not ground truth. Document this honestly. GitHub commits prove volume, not quality. Certifications prove exam-passing, not mastery. This intellectual honesty is what makes the feature CV-worthy.

---

### Agent 2: Interview Agent (Human-in-the-Loop)

**What it does:** Conducts a targeted skill verification conversation to strengthen weak proof scores.

**What you'll learn:**
- LangGraph's `interrupt()` mechanism for HITL
- Conditional edge routing based on confidence thresholds
- Conversation state management across turns
- Prompt engineering for structured questioning

**How it works:**
1. Reviews the profile from Agent 1
2. Identifies skills with proof_score < 0.5 (low confidence)
3. Generates 3-7 targeted questions (not open-ended interrogation)
4. Each answer updates the proof score for that skill
5. Loop continues until all key skills exceed confidence threshold OR max 7 questions reached
6. User can skip at any time â†’ proceeds with current scores

**Example Question Flow:**
```
Agent: "Your resume mentions React, but I don't see React projects on your
       GitHub. Can you describe a React project you've built and what state
       management approach you used?"

User:  "I built a dashboard using React + Zustand for a college project..."

Agent: [Updates React proof_score from 0.3 â†’ 0.6 based on technical depth]
Agent: "Got it. You mention Python â€” have you worked with any async frameworks
       like FastAPI or used Python for data pipelines?"
```

> [!TIP]
> **UX Critical:** Cap at 7 questions max. Show a progress bar ("3/7 questions"). Let user skip. If you interrogate too long, users drop off. The skip mechanism is essential.

---

### Agent 3: Job Search Agent

**What it does:** Queries multiple job APIs with intelligently generated search variants.

**What you'll learn:**
- Multi-source API integration and normalization
- Query generation from structured profiles (not just job title search)
- Rate limiting and retry strategies
- Data deduplication across sources

**The Job Data Strategy (India-Focused):**

| Source | Coverage | Cost | What It Gets You |
|---|---|---|---|
| **SerpAPI (Google Jobs)** | Aggregates LinkedIn, Naukri, Indeed via Google | ~$25/mo, 100 free searches | Best single source â€” Google indexes most Indian job boards |
| **Adzuna API** | India + 19 other countries | Free tier: 2,500 hits/month | Salary data, location, category tags |
| **Jooble API** | India-supported, free | Free with API key | Good volume, simple integration |
| **Remotive API** | Remote jobs globally | Free, max 4 req/day | Remote tech jobs |
| **Himalayas API** | Remote jobs | Free, no API key needed | Salary, timezone, seniority data |
| **JobSpy (Open Source)** | LinkedIn, Indeed, Glassdoor scraping | Free (OSS library) | Backup/supplementary, use carefully |

> [!WARNING]
> **Do NOT scrape LinkedIn/Naukri directly.** LinkedIn actively litigates. Naukri uses Akamai anti-bot. Use API aggregators (SerpAPI/Adzuna/Jooble) that index these platforms legitimately. JobSpy is a backup for development/testing only.

**Query Generation Strategy:**
Instead of searching just "Frontend Developer", the agent generates 3-5 query variants:
```python
# From profile: {primary_role: "Frontend Developer", skills: ["React", "TypeScript", "Next.js"]}
queries = [
    "Frontend Developer React",
    "React Developer",
    "UI Engineer TypeScript",
    "Full Stack Developer Next.js",
    "Software Engineer Frontend"
]
# Each query goes to each API â†’ normalized â†’ deduplicated
```

**Normalization Schema:**
All jobs from all sources get normalized into a unified `JobListing` schema:
```python
class JobListing(BaseModel):
    id: str                    # Internal unique ID
    source: str                # "serpapi" | "adzuna" | "jooble" | etc.
    title: str
    company: str
    location: str
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_is_predicted: bool
    description: str           # Full JD text
    posting_date: datetime
    url: str                   # Apply link
    employment_type: str       # full_time, contract, etc.
    raw_data: dict             # Original API response preserved
```

---

### Agent 4: JD Analyzer Agent

**What it does:** Deep-parses each job description to extract structured requirements and embeds them for matching.

**What you'll learn:**
- LLM-based information extraction from unstructured text
- Text embedding generation (OpenAI `text-embedding-3-small` or `all-MiniLM-L6-v2`)
- ChromaDB vector storage and similarity search
- Hybrid search: BM25 keyword + vector semantic

**How it works:**
1. Takes each `JobListing` from Agent 3
2. LLM extracts structured requirements:
   ```python
   class JDRequirements(BaseModel):
       required_skills: List[SkillRequirement]  # skill + level + is_mandatory
       experience_years_min: int
       experience_years_max: Optional[int]
       education: Optional[str]
       implicit_signals: List[str]  # "startup culture", "fast-paced", etc.
       red_flags: List[str]         # Detected issues
   ```
3. Generates embedding of full JD text â†’ stores in ChromaDB
4. Runs ghost job detection heuristics on each listing

**Ghost Job Detection Signals:**

| Signal | Weight | Logic |
|---|---|---|
| Posting age > 30 days | High | Old listing without repost = likely stale/ghost |
| JD text similarity > 0.92 with other listings from same company | High | Copy-paste recycled JDs |
| Vague requirements ("good communication skills" as only requirement) | Medium | Placeholder listings |
| No salary range + "competitive salary" | Low | Common but suspicious when combined |
| Company has multiple identical roles posted simultaneously | Medium | Pipeline building signal |

Output: Each job gets a `listing_health_score` (0-1) and a `ghost_probability` label.

---

### Agent 5: Matching & Ranking Agent

**What it does:** Scores every job against the user's profile and buckets into 3 tiers.

**What you'll learn:**
- Cosine similarity scoring with embedding vectors
- Multi-dimensional scoring with weighted factors
- Ranking algorithms and tier classification
- The math behind recommendation systems

**Scoring Formula:**
```
match_score = weighted_sum(
    skill_overlap_score     Ã— 0.35,  # % of required skills user has (proof-weighted)
    experience_delta_score  Ã— 0.20,  # How close user's years match requirement
    embedding_similarity    Ã— 0.25,  # Cosine similarity of profileâ†”JD embeddings
    proof_alignment_score   Ã— 0.20   # Higher proof scores on matching skills = higher
)
```

**3-Tier Classification:**

| Tier | Criteria | What User Sees |
|---|---|---|
| ðŸŸ¢ **Easy Gets** | match_score > 0.80, user exceeds requirements | "You're overqualified. High chance of callback." |
| ðŸŸ¡ **Best Matches** | 0.55 < match_score â‰¤ 0.80 | "Good fit. These align with your verified skills." |
| ðŸ”´ **Stretch Goals** | 0.30 < match_score â‰¤ 0.55 | "Reach roles. Here's what you're missing: [skills]" |

Jobs with match_score < 0.30 are filtered out entirely. Jobs with ghost_probability > 0.7 get flagged visually.

---

### Agent 6: Output & Roadmap Agent

**What it does:** Generates the final output: job cards, per-job tailored resume suggestions, and on-demand skill gap roadmaps.

**What you'll learn:**
- LLM-based content generation with tight constraints
- PDF generation with `WeasyPrint` or `reportlab`
- On-demand sub-agent invocation (roadmap generation)

**Features:**
1. **Job Cards** â€” Structured output per job with tier label, match score breakdown, company health signals, ghost badge
2. **Resume Tailoring** â€” For each shortlisted job, suggests bullet point reordering and keyword additions to maximize ATS score
3. **Skill Gap Roadmap** â€” On-demand for stretch goals: "You lack Kubernetes. Here's a 4-week roadmap: [structured plan]"

---

## Tech Stack (Final Decision)

| Layer | Technology | Why |
|---|---|---|
| **Backend** | FastAPI (Python 3.11+) | Async-native, perfect for streaming + agent orchestration |
| **Agent Framework** | LangGraph | StateGraph with checkpointing, HITL, conditional edges â€” exactly what this needs |
| **LLM Gateway** | LiteLLM Proxy | Unified API across OpenAI/Gemini/Claude, token tracking, budget caps |
| **Vector DB** | ChromaDB | Open-source, easy local setup, good for this scale |
| **Relational DB** | PostgreSQL | LangGraph checkpointing + user data + job cache |
| **Cache / Queue** | Redis | Session state + Celery task queue for async JD parsing |
| **Frontend** | React + Vite | SPA with streaming chat UI, job dashboard, profile viewer |
| **PDF Parsing** | pdfplumber | Best Python PDF text extractor for resumes |
| **Embeddings** | `text-embedding-3-small` (OpenAI) or `all-MiniLM-L6-v2` (local) | Cost vs speed tradeoff |
| **Tracing** | LangSmith | Full agent trajectory logging, debugging, evaluation |
| **Deployment** | Docker Compose | All services (FastAPI, Postgres, Redis, ChromaDB, LiteLLM) containerized |

---

## LangGraph State Machine (The Brain)

```mermaid
stateDiagram-v2
    [*] --> ProfileBuilder: User uploads resume
    ProfileBuilder --> Interview: Profile extracted (has low-confidence skills)
    ProfileBuilder --> JobSearch: All skills high-confidence (skip interview)
    
    Interview --> Interview: User answers question (loop)
    Interview --> JobSearch: Confidence threshold met OR max questions OR user skips
    
    JobSearch --> JDAnalyzer: Jobs fetched from APIs
    JDAnalyzer --> MatchRank: JDs parsed + embedded + ghost-checked
    MatchRank --> Output: Jobs scored + tiered
    
    Output --> [*]: Results displayed
    Output --> RoadmapGen: User requests roadmap for skill gap
    RoadmapGen --> Output: Roadmap generated
    
    Output --> ResumeTailor: User requests tailored resume for job
    ResumeTailor --> Output: Tailored resume PDF generated
```

**Key LangGraph Concepts Used:**
- **StateGraph** â€” The entire pipeline is one graph with shared state
- **Checkpointing** â€” PostgresSaver persists state after every node â†’ user can resume anytime
- **interrupt()** â€” Interview node pauses execution, waits for user input via API
- **Conditional Edges** â€” Routing based on confidence scores, user choices
- **Send()** â€” Fan-out JD analysis across multiple jobs in parallel
- **Tool Nodes** â€” API calls (SerpAPI, GitHub, Adzuna) wrapped as LangGraph tools

---

## Data Flow (End-to-End)

```
User uploads resume.pdf
        â”‚
        â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Profile Builder     â”‚ â†’ pdfplumber â†’ LLM extraction â†’ GitHub API
â”‚  Output: UserProfile â”‚   {skills: [{name, level, proof_score, evidence[]}]}
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Interview Agent     â”‚ â†’ Asks 3-7 targeted questions
â”‚  Updates: proof_scoresâ”‚  â†’ Each answer updates scores
â”‚  Uses: interrupt()   â”‚  â†’ User can skip anytime
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Job Search Agent    â”‚ â†’ SerpAPI + Adzuna + Jooble + Remotive
â”‚  Output: JobListing[]â”‚   â†’ Generates 3-5 query variants per profile
â”‚  Normalized + Dedupedâ”‚   â†’ ~50-200 unique jobs
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  JD Analyzer Agent   â”‚ â†’ LLM extracts requirements from each JD
â”‚  Output:             â”‚   â†’ Generates embeddings â†’ ChromaDB
â”‚  - JDRequirements[]  â”‚   â†’ Ghost job detection heuristics
â”‚  - Embeddings stored â”‚   â†’ Listing health scores
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Matching Agent      â”‚ â†’ Cosine similarity + multi-factor scoring
â”‚  Output:             â”‚   â†’ 3-tier classification
â”‚  - Scored job list   â”‚   â†’ Skill gap identification per job
â”‚  - 3 tiers           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚
          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Output Agent        â”‚ â†’ Job cards with scores, badges, company intel
â”‚  + Resume Tailor     â”‚   â†’ Per-job resume suggestions (on-demand)
â”‚  + Roadmap Gen       â”‚   â†’ Skill gap roadmaps (on-demand)
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Project Structure

```
True Job/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ main.py              # FastAPI app entry point
â”‚   â”‚   â”œâ”€â”€ config.py            # Settings, env vars, API keys
â”‚   â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”‚   â”œâ”€â”€ routes/
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ chat.py      # SSE streaming chat endpoint
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ profile.py   # Upload resume, get profile
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ jobs.py      # Job results, tailored resume, roadmap
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ health.py    # Health check
â”‚   â”‚   â”‚   â””â”€â”€ deps.py          # Dependency injection
â”‚   â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”‚   â”œâ”€â”€ graph.py         # Main LangGraph StateGraph definition
â”‚   â”‚   â”‚   â”œâ”€â”€ state.py         # Shared state schema (TypedDict)
â”‚   â”‚   â”‚   â”œâ”€â”€ supervisor.py    # Supervisor node logic
â”‚   â”‚   â”‚   â”œâ”€â”€ profile_builder.py
â”‚   â”‚   â”‚   â”œâ”€â”€ interviewer.py   # HITL interview loop
â”‚   â”‚   â”‚   â”œâ”€â”€ job_searcher.py
â”‚   â”‚   â”‚   â”œâ”€â”€ jd_analyzer.py
â”‚   â”‚   â”‚   â”œâ”€â”€ matcher.py
â”‚   â”‚   â”‚   â””â”€â”€ output_agent.py
â”‚   â”‚   â”œâ”€â”€ tools/
â”‚   â”‚   â”‚   â”œâ”€â”€ pdf_parser.py    # pdfplumber wrapper
â”‚   â”‚   â”‚   â”œâ”€â”€ github_api.py    # GitHub profile analysis
â”‚   â”‚   â”‚   â”œâ”€â”€ serpapi.py       # SerpAPI Google Jobs
â”‚   â”‚   â”‚   â”œâ”€â”€ adzuna.py        # Adzuna API client
â”‚   â”‚   â”‚   â”œâ”€â”€ jooble.py        # Jooble API client
â”‚   â”‚   â”‚   â”œâ”€â”€ remotive.py      # Remotive API client
â”‚   â”‚   â”‚   â””â”€â”€ himalayas.py     # Himalayas API client
â”‚   â”‚   â”œâ”€â”€ models/
â”‚   â”‚   â”‚   â”œâ”€â”€ user_profile.py  # Pydantic schemas for profile
â”‚   â”‚   â”‚   â”œâ”€â”€ job_listing.py   # Normalized job schema
â”‚   â”‚   â”‚   â”œâ”€â”€ jd_requirements.py
â”‚   â”‚   â”‚   â””â”€â”€ matching.py      # Scoring models
â”‚   â”‚   â”œâ”€â”€ services/
â”‚   â”‚   â”‚   â”œâ”€â”€ embedding.py     # Embedding generation + ChromaDB
â”‚   â”‚   â”‚   â”œâ”€â”€ ghost_detector.py # Ghost job detection logic
â”‚   â”‚   â”‚   â”œâ”€â”€ resume_tailor.py # Per-job resume tailoring
â”‚   â”‚   â”‚   â””â”€â”€ roadmap_gen.py   # Skill gap roadmap generation
â”‚   â”‚   â””â”€â”€ db/
â”‚   â”‚       â”œâ”€â”€ postgres.py      # PostgreSQL connection + checkpointer
â”‚   â”‚       â””â”€â”€ redis_client.py  # Redis session + cache
â”‚   â”œâ”€â”€ tests/
â”‚   â”‚   â”œâ”€â”€ test_profile_builder.py
â”‚   â”‚   â”œâ”€â”€ test_interview.py
â”‚   â”‚   â”œâ”€â”€ test_job_search.py
â”‚   â”‚   â”œâ”€â”€ test_matching.py
â”‚   â”‚   â””â”€â”€ test_ghost_detector.py
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â”œâ”€â”€ Dockerfile
â”‚   â””â”€â”€ .env.example
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ App.jsx
â”‚   â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”‚   â”œâ”€â”€ ChatPanel/       # Streaming chat with agent
â”‚   â”‚   â”‚   â”œâ”€â”€ ProfileCard/     # Visual skill profile with proof scores
â”‚   â”‚   â”‚   â”œâ”€â”€ JobCard/         # Individual job with tier badge
â”‚   â”‚   â”‚   â”œâ”€â”€ JobBoard/        # 3-column tier view
â”‚   â”‚   â”‚   â”œâ”€â”€ RoadmapView/     # Skill gap roadmap display
â”‚   â”‚   â”‚   â””â”€â”€ ResumeUpload/    # PDF upload + drag-drop
â”‚   â”‚   â”œâ”€â”€ hooks/
â”‚   â”‚   â”‚   â”œâ”€â”€ useSSE.js        # Server-Sent Events hook
â”‚   â”‚   â”‚   â””â”€â”€ useChat.js       # Chat state management
â”‚   â”‚   â””â”€â”€ services/
â”‚   â”‚       â””â”€â”€ api.js           # API client
â”‚   â”œâ”€â”€ package.json
â”‚   â””â”€â”€ vite.config.js
â”œâ”€â”€ docker-compose.yml           # All services
â”œâ”€â”€ litellm_config.yaml          # LLM routing + budgets
â””â”€â”€ README.md
```

---

## Build Phases

### Phase 1: Foundation (Week 1)
> **Goal:** Resume â†’ Structured Profile with proof scores

- [ ] Set up project structure (FastAPI + React + Docker Compose)
- [ ] Implement PDF parser tool (`pdfplumber`)
- [ ] Build `UserProfile` Pydantic schema with proof score model
- [ ] Build Profile Builder agent (LangGraph node)
- [ ] Implement GitHub API tool for skill evidence
- [ ] Set up PostgreSQL + LangGraph checkpointing
- [ ] Build basic chat UI with SSE streaming
- [ ] **Test:** Upload resume â†’ get structured profile with scores

### Phase 2: Interview Loop (Week 2)
> **Goal:** HITL interview agent that strengthens proof scores

- [ ] Implement Interview Agent with `interrupt()` pattern
- [ ] Build conditional routing (skip if all scores > threshold)
- [ ] Design question generation prompts (targeted, not generic)
- [ ] Implement proof score update logic based on answers
- [ ] Add skip mechanism + progress indicator
- [ ] Connect chat UI to interview flow with streaming
- [ ] **Test:** Full flow â€” upload resume â†’ interview â†’ finalized profile

### Phase 3: Job Search Pipeline (Week 3)
> **Goal:** Multi-source job search with normalization

- [ ] Implement SerpAPI Google Jobs tool (primary source)
- [ ] Implement Adzuna API tool
- [ ] Implement Jooble API tool
- [ ] Implement Remotive + Himalayas API tools
- [ ] Build query generation logic (profile â†’ multiple search queries)
- [ ] Implement job normalization and deduplication
- [ ] Build Job Search Agent (LangGraph node)
- [ ] **Test:** Profile â†’ 50-200 normalized, deduplicated jobs

### Phase 4: JD Analysis + Matching (Week 4)
> **Goal:** Semantic JD analysis, embedding, matching, 3-tier output

- [ ] Implement JD Analyzer Agent (LLM-based requirements extraction)
- [ ] Set up ChromaDB + embedding generation
- [ ] Implement ghost job detection heuristics
- [ ] Build Matching Agent with multi-factor scoring
- [ ] Implement 3-tier classification logic
- [ ] Build Output Agent with job cards
- [ ] Build job board UI (3-column tier view)
- [ ] **Test:** End-to-end: resume â†’ interview â†’ jobs â†’ tiered results

### Phase 5: Advanced Features (Week 5)
> **Goal:** Resume tailoring, roadmaps, ghost badges, polish

- [ ] Implement per-job resume tailoring engine
- [ ] Implement on-demand skill gap roadmap generation
- [ ] Add ghost job badges + listing health scores to UI
- [ ] Implement salary intelligence (from Adzuna salary data)
- [ ] Add company intelligence cards (if API budget allows)
- [ ] Set up LiteLLM proxy for cost management
- [ ] Set up LangSmith tracing
- [ ] Polish UI â€” dark mode, animations, mobile responsive
- [ ] Write comprehensive README + proof score methodology doc
- [ ] **Test:** Full system test with real resumes

---

## User Review Required

> [!IMPORTANT]
> **LLM Provider Choice:** This plan assumes OpenAI API for main LLM calls and embeddings. Gemini (free tier) is a viable alternative for development. Which LLM provider(s) do you want to use? This affects cost and model routing strategy.

> [!IMPORTANT]
> **Budget Reality:** SerpAPI ($25/mo for 5,000 searches), OpenAI API (~$5-20/mo depending on usage), LangSmith (free tier available). Total estimated cost: **â‚¹3,000-5,000/month** during development. Are you comfortable with this?

> [!WARNING]
> **Scope vs. Time:** This plan is 5 weeks for a focused developer. If you're doing this alongside coursework/other projects, budget 7-8 weeks. Phase 1-4 is the MVP. Phase 5 is the differentiator. Don't skip Phase 5's resume tailoring and ghost detection â€” that's what makes this CV-worthy.

## Open Questions

> [!IMPORTANT]
> 1. **LLM Provider:** OpenAI API, Google Gemini (free tier for dev), or both via LiteLLM routing?
> 2. **Hosting Plan:** Local development only, or do you want to deploy (Railway, Render, etc.)?
> 3. **India-Specific Scope:** Starting with tech jobs in India (Bangalore, Mumbai, Hyderabad, Delhi, Pune, Chennai, remote). Correct?
> 4. **Authentication:** Do you want user accounts (login/signup) or is this a single-user tool for now?
> 5. **Name Confirmation:** "SAMAS" â€” the workspace is "True Job". Happy with this name?

## Verification Plan

### Automated Tests
```bash
# Unit tests for each agent
pytest backend/tests/ -v

# Integration test: full pipeline
pytest backend/tests/test_integration.py -v

# LangSmith evaluation traces
# Run evaluation dataset through pipeline, check trajectory quality
```

### Manual Verification
- Upload 3-5 real resumes with varying experience levels
- Verify proof scores make sense (junior vs senior profiles)
- Check job results against manual Google Jobs search
- Validate ghost detection on known stale listings
- Test cross-session persistence (upload â†’ close â†’ reopen â†’ resume)
- Verify SSE streaming works smoothly in the UI
