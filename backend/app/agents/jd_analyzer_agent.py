import json
import asyncio
from typing import List, Dict, TypedDict, Annotated, Any
import operator
import numpy as np

# LangChain / LangGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Local
from app.llm import call_llm_with_fallback, get_embedder
from app.models.job import JobListing
from app.models.jd_requirements import JDRequirements
from app.tools.text_utils import get_similar_company_jobs, clean_html
from app.tools.ghost_detector import calculate_ghost_probability
from app.utils.pinecone_hybrid import hybrid_upsert

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
import os

_EMBEDDER = None

class BatchAnalysisState(TypedDict):
    """State for the batched LLM parsing."""
    jobs: List[JobListing]
    results: Annotated[List[Dict], operator.add]
    errors: Annotated[List[str], operator.add]


class JDAnalyzerState(TypedDict):
    """Main state for the JD Analyzer Agent."""
    raw_jobs: List[JobListing]
    unique_jobs: List[JobListing]
    
    # User profile for keyword pre-filtering
    user_profile: dict
    
    # Pre-filter results
    filtered_jobs: List[JobListing]     # Jobs that passed keyword relevance check
    dropped_jobs: List[JobListing]      # Jobs dropped by pre-filter (for transparency)
    
    # Text similarity map for ghost detection
    similar_job_map: Dict[str, List[str]]
    
    # Batched jobs
    job_batches: List[List[JobListing]]
    
    # Extracted requirements (job_id -> JDRequirements dict)
    extracted_requirements: Dict[str, dict]
    
    search_location: str
    
    # Vector store paths
    vector_store_ready: bool




# ═══════════════════════════════════════════════════════
# NODE 1: DEEP DEDUPLICATION & SIMILARITY
# ═══════════════════════════════════════════════════════
def deep_deduplication_node(state: JDAnalyzerState) -> dict:
    """Find highly similar jobs from the same company and flag them."""
    jobs = state.get("raw_jobs", [])
    print(f"\n[JD Analyzer] Step 1: Deep Deduplication & Similarity Mapping ({len(jobs)} jobs)")
    
    # Clean HTML first
    for j in jobs:
        j.description = clean_html(j.description)
        
    # Get similarity map (Threshold 0.92 = highly similar/copy-paste)
    similar_map = get_similar_company_jobs([j.model_dump() for j in jobs], threshold=0.92)
    
    # We could drop duplicates here, but for now we just flag them for ghost detection
    # because sometimes a company actually posts 10 identical roles for different teams.
    # The Ghost Detector will penalize this.
    
    print("   Similarity mapping complete.")
    return {
        "unique_jobs": jobs,
        "similar_job_map": similar_map
    }


# ═══════════════════════════════════════════════════════
# NODE 2: KEYWORD PRE-FILTER (Cost: ZERO)
# ═══════════════════════════════════════════════════════

def keyword_prefilter_node(state: JDAnalyzerState) -> dict:
    """Fast BM25 Pre-filter: rank jobs by keyword overlap and drop the bottom 25%.
    
    This is the first layer of the Filtering Funnel pattern:
        Fast BM25 Filter → Expensive LLM → Precise embeddings
    
    We drop the bottom 25% of jobs to save LLM tokens and latency. 
    LangSmith traces will allow us to observe if this threshold should be adjusted.
    """
    jobs = state.get("unique_jobs", [])
    profile = state.get("user_profile", {})
    
    # Collect ALL skill names from the user profile
    user_skills = []
    for skill in profile.get("skills", []):
        name = skill.get("name", "")
        if name:
            user_skills.append(name)
            # Also add the parent_domain as a broader match
            domain = skill.get("parent_domain", "")
            if domain and domain.lower() not in [s.lower() for s in user_skills]:
                user_skills.append(domain)
    
    if not user_skills:
        print(f"   No user skills found — skipping pre-filter (all {len(jobs)} jobs pass)")
        return {"filtered_jobs": jobs, "dropped_jobs": []}
    
    print(f"\n[JD Analyzer] Step 2: Keyword Pre-Filter (BM25) ({len(jobs)} jobs vs {len(user_skills)} skills)")
    
    import math
    from rank_bm25 import BM25Okapi
    
    # Prepare corpus for BM25
    tokenized_corpus = [job.description.lower().split() for job in jobs]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Prepare query
    tokenized_query = " ".join(user_skills).lower().split()
    
    # Get scores
    doc_scores = bm25.get_scores(tokenized_query)
    
    job_scores = list(zip(jobs, doc_scores))
    
    # Rank jobs (highest score first)
    job_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Drop bottom 25%
    drop_count = math.floor(len(jobs) * 0.25)
    keep_count = len(jobs) - drop_count
    
    filtered = []
    dropped = []
    
    for i, (job, score) in enumerate(job_scores):
        if i >= keep_count:
            job.pipeline_status = "dropped"
            if not getattr(job, 'metadata', None):
                job.metadata = {}
            job.metadata["drop_reason"] = f"Low BM25 overlap score: {score:.2f}"
            dropped.append(job)
        else:
            filtered.append(job)
            
    print(f"   Passed: {len(filtered)} jobs | Dropped: {len(dropped)} (BM25 bottom 25%)")
    if dropped:
        dropped_titles = [f"{j.title} [{j.metadata.get('drop_reason')}]" for j in dropped[:5]]
        print(f"   Sample dropped: {', '.join(dropped_titles)}")
    
    return {"filtered_jobs": filtered, "dropped_jobs": dropped}


# ═══════════════════════════════════════════════════════
# NODE 3: BATCHING
# ═══════════════════════════════════════════════════════

def batch_jobs_node(state: JDAnalyzerState) -> dict:
    """Split FILTERED jobs into batches of 8 for the LLM."""
    # Use filtered_jobs (post pre-filter), not unique_jobs (pre pre-filter)
    jobs = state.get("filtered_jobs", state.get("unique_jobs", []))
    
    # Only batch jobs that have a full description (> 300 chars)
    full_jobs = [j for j in jobs if len(j.description) > 300]
    
    batch_size = 8
    batches = [full_jobs[i:i + batch_size] for i in range(0, len(full_jobs), batch_size)]
    
    print(f"   Split {len(full_jobs)} full JDs into {len(batches)} batches (saved from {len(state.get('unique_jobs', []))} original).")
    
    return {"job_batches": batches}


# ═══════════════════════════════════════════════════════
# NODE 3: LLM EXTRACTION (Process all batches sequentially)
# ═══════════════════════════════════════════════════════

from langchain_core.runnables import RunnableConfig

async def extract_requirements_node(state: JDAnalyzerState, config: RunnableConfig) -> dict:
    """Extract structured requirements using LLM for all batches."""
    batches = state.get("job_batches", [])
    extracted = {}
    
    print(f"   [JD Analyzer] Step 2: Extracting JD Requirements ({len(batches)} batches)...")
    
    # Extract BYOK Config
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    custom_model = configurable.get("custom_model")
    
    # We process sequentially to avoid rate limits on free-tier keys
    for i, batch in enumerate(batches):
        print(f"      Processing batch {i+1}/{len(batches)} ({len(batch)} jobs)...")
        
        # Build prompt
        prompt = "Extract structured requirements for the following Job Descriptions.\n\n"
        for idx, job in enumerate(batch):
            prompt += f"--- JOB ID: {job.id} ---\n"
            prompt += f"Title: {job.title}\nCompany: {job.company}\n\n"
            # Limit description to 4000 chars to save context
            prompt += f"{job.description[:4000]}\n\n"
            
        sys_msg = SystemMessage(content='''You are an elite Tech Recruiter.
Analyze the provided job descriptions and return a JSON dictionary mapping the JOB ID to its extracted JDRequirements.

For each job, extract:
- required_skills: list of {name: str, level: "beginner"|"intermediate"|"advanced"|"unspecified", is_mandatory: bool}
- experience_years_min: integer (0 if none)
- experience_years_max: integer or null
- education: string or null
- implicit_signals: list of strings (e.g. "fast-paced", "startup")
- red_flags: list of strings (e.g. "wear many hats")
- ghost_probability: float 0.0 to 1.0 (Estimate if this is a "ghost/fake/stale" job. Hints: extreme vagueness, "always looking for" evergreen language, or impossible combinations of skills = high probability)
- ghost_reasoning: string
- extracted_salary: string (extract the compensation/salary if mentioned, otherwise null)

Return ONLY valid JSON matching this schema:
{
  "JOB_ID_1": {
    "required_skills": [...],
    ...
  },
  "JOB_ID_2": { ... }
}''')
        
        try:
            resp = await call_llm_with_fallback(
                [sys_msg, HumanMessage(content=prompt)], 
                label="JD Analyzer",
                custom_api_key=custom_api_key,
                custom_model=custom_model,
                config=config
            )
            data = resp["data"]
            
            # Merge into results
            for job_id, reqs in data.items():
                extracted[job_id] = reqs
                
        except Exception as e:
            print(f"      Error processing batch {i+1}: {e}")
            
    return {"extracted_requirements": extracted}


# ═══════════════════════════════════════════════════════
# NODE 4: APPLY GHOST HEURISTICS & CREATE VECTORS
# ═══════════════════════════════════════════════════════

async def finalize_and_embed_node(state: JDAnalyzerState, config: RunnableConfig) -> dict:
    """Apply heuristics, create the final objects, and embed them."""
    jobs = state.get("unique_jobs", [])
    extracted = state.get("extracted_requirements", {})
    similar_map = state.get("similar_job_map", {})
    
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    
    print(f"\n   [JD Analyzer] Step 3: Applying Ghost Heuristics & Computing Vectors")
    
    # 1. Update extracted with heuristic ghost scoring
    final_extracted = {}
    texts_to_embed = []
    job_ids = []
    
    for job in jobs:
        # If it wasn't extracted (snippet), create empty requirements
        if job.id not in extracted:
            reqs = JDRequirements(
                required_skills=[],
                implicit_signals=[],
                red_flags=[],
                ghost_probability=0.0,
                ghost_reasoning="Snippet only. Cannot analyze.",
                extracted_salary=None
            )
        else:
            try:
                reqs = JDRequirements(**extracted[job.id])
            except Exception as e:
                # If LLM messed up the schema, fallback
                reqs = JDRequirements(required_skills=[], implicit_signals=[], red_flags=[])
                
        # Apply heuristics
        sim_count = len(similar_map.get(job.id, []))
        final_prob, signals = calculate_ghost_probability(job, reqs, sim_count, reqs.ghost_probability)
        
        reqs.ghost_probability = final_prob
        if signals:
            reqs.ghost_reasoning += " | Heuristics triggered: " + ", ".join(signals)
            
        final_extracted[job.id] = reqs.model_dump()
        
        # 2. Prepare text for embedding
        # We embed the title, location, skills, and the first 1000 chars of the description
        skills_text = ", ".join([s.name for s in reqs.required_skills])
        embed_text = f"Title: {job.title}. Location: {job.location}. Skills: {skills_text}. Description: {job.description[:1000]}"
        texts_to_embed.append(embed_text)
        job_ids.append(job.id)
        
    # 3. Create Pinecone Index (Upsert)
    try:
        if not texts_to_embed:
            print("   No jobs to embed. Skipping Pinecone indexing.")
            return {
                "extracted_requirements": final_extracted,
                "vector_store_ready": False
            }
            
        embedder = get_embedder(custom_api_key=custom_api_key)
        print("      Computing embeddings and uploading to Pinecone...")
        
        # Prepare metadata for Pinecone
        metadatas = [{"job_id": j_id} for j_id in job_ids]
        
        index_name = os.environ.get("PINECONE_INDEX_NAME", "samas-index")
        
        from app.utils.pinecone_hybrid import hybrid_upsert
        await asyncio.to_thread(
            hybrid_upsert,
            texts=texts_to_embed,
            metadatas=metadatas,
            embedder=embedder,
            index_name=index_name
        )
            
        print("   Pinecone index successfully updated.")
        ready = True
        
    except Exception as e:
        print(f"   Error creating embeddings: {e}")
        ready = False
        
    return {
        "extracted_requirements": final_extracted,
        "vector_store_ready": ready
    }

# ═══════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════

def build_jd_analyzer_graph() -> StateGraph:
    builder = StateGraph(JDAnalyzerState)
    
    builder.add_node("deep_deduplication", deep_deduplication_node)
    builder.add_node("keyword_prefilter", keyword_prefilter_node)
    builder.add_node("batch_jobs", batch_jobs_node)
    builder.add_node("extract_requirements", extract_requirements_node)
    builder.add_node("finalize_and_embed", finalize_and_embed_node)
    
    # The Filtering Funnel:
    # dedup (free) → keyword filter (free) → batch → LLM extract (expensive) → embed
    builder.add_edge(START, "deep_deduplication")
    builder.add_edge("deep_deduplication", "keyword_prefilter")
    builder.add_edge("keyword_prefilter", "batch_jobs")
    builder.add_edge("batch_jobs", "extract_requirements")
    builder.add_edge("extract_requirements", "finalize_and_embed")
    builder.add_edge("finalize_and_embed", END)
    
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
