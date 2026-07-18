# SAMAS: Required Fixes & Tech Debt

This document tracks identified discrepancies between the documentation/claims and the actual implementation, along with action items to resolve them.

### 1. Guardrails AI Implementation
- **Issue:** The `README` overclaims Guardrails security (prompt-injection protection). Currently, `guardrails-ai` is only used to enforce the JSON schema via `Guard.from_pydantic()` after the LLM generates output.
- **Fix Needed:** 
  - Install the prompt injection hub validator: `guardrails hub install hub://guardrails/detect_prompt_injection`
  - Wrap the actual LLM call inside the `guard()` execution rather than just using it for post-generation parsing in `profile_builder.py`.

### 2. Testing Dependencies Missing
- **Issue:** `pytest` and `deepeval` were installed in the virtual environment but missing from `backend/requirements.txt`.
- **Fix Needed:** Add `pytest>=8.0.0` and `deepeval>=1.0.0` to `requirements.txt`.

### 3. Job Scraping Scale
- **Issue:** The code only fetches `max_pages=1` from SerpAPI and caps results to 25 jobs to prevent rate limits and save tokens, contradicting the "100+ global jobs" claim.
- **Fix Needed:** Either update the SerpAPI pagination logic in `job_search_agent.py` to loop through multiple pages and remove the hard 25-job slice, or keep it as-is for performance and ensure documentation accurately states it uses "highly targeted, token-efficient batching".

### 4. Deduplication Logic Placement
- **Issue:** `jd_analyzer_agent.py` mentions "deep deduplication" in its graph structure, but the actual deduping logic is executed upstream in `job_search_agent.py`.
- **Fix Needed:** Clean up the graph node naming and comments in `jd_analyzer_agent.py` to reflect that it assumes incoming jobs are already deduplicated.

### 5. Matching Agent Result Truncation
- **Issue:** `matching_agent.py` scores and returns all matched jobs rather than strictly slicing the `top 5`.
- **Fix Needed:** Add a `matched_jobs = matched_jobs[:5]` slice at the end of the matching node in `matching_agent.py`.

### 6. Pinecone Index Isolation
- **Issue:** `hybrid_upsert` generates a random UUID for every vector without utilizing Pinecone namespaces. This means subsequent runs for the same user or different users pollute the shared index.
- **Fix Needed:** Pass a `namespace=session_id` to the Pinecone upsert and query functions in `pinecone_hybrid.py` to strictly isolate cross-run data.

### 7. Frontend Profile Summary Mapping
- **Issue:** Frontend looks for `profile.professional_summary` instead of the deeply nested `profile.personal_info.professional_summary`.
- **Fix Needed:** Update `page.tsx` line 473 to safely map `profile?.personal_info?.professional_summary`.

### 8. Security (CORS & API Keys)
- **Issue:** CORS in FastAPI is `allow_origins=["*"]`, and the frontend sends API keys from the client to the backend over HTTP requests.
- **Fix Needed:** Restrict CORS to `localhost:3000` or the production domain. Move API keys strictly to the backend `.env` (removing BYOK from the frontend payload) for true enterprise security.

### 9. Licensing
- **Issue:** No `LICENSE` file in the repository.
- **Fix Needed:** Add a standard `LICENSE` file to the repo root.

### 10. Frontend Linting
- **Issue:** `npm run lint` fails with React hook purity and `any` type errors.
- **Fix Needed:** Refactor `any` types in components like `OracleResults.tsx` and address hook dependencies in the `mirror-dimension` directory.
