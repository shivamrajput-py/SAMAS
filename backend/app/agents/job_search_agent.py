import operator
import json
from typing import TypedDict, List, Annotated

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.llm import call_llm_with_fallback
from app.models.job import JobListing
from app.tools.serpapi import search_serpapi


# ═══════════════════════════════════════════════════════
# STATE DEFINITIONS
# ═══════════════════════════════════════════════════════

class JobSearchState(TypedDict, total=False):
    """Main state for the Job Search Agent."""
    user_profile: dict
    location: str
    suggested_titles: List[str]
    selected_titles: List[str]
    # Annotated with operator.add so that parallel Send() results are merged into a single list
    job_listings: Annotated[List[JobListing], operator.add]
    deduplicated_jobs: List[JobListing]
    errors: Annotated[List[str], operator.add]
    status: str

class TitleSearchState(TypedDict):
    """State for the search subgraph (runs once per selected title)."""
    search_title: str
    location: str
    # These will bubble up and merge into the parent state
    job_listings: Annotated[List[JobListing], operator.add]
    errors: Annotated[List[str], operator.add]


# ═══════════════════════════════════════════════════════
# NODE 1 & 2: SUGGEST & SELECT TITLES
# ═══════════════════════════════════════════════════════

def _build_title_suggestion_prompt(profile: dict) -> str:
    """Build the prompt to suggest 3 job titles based on the user's verified skills."""
    skills = profile.get("skills", [])
    
    # Filter to high-proof skills to inform the titles
    strong_skills = [s["name"] for s in skills if s.get("proof_score", 0) >= 0.5]
    
    # Include all skills if they don't have enough strong ones
    if len(strong_skills) < 3:
        strong_skills = [s["name"] for s in skills][:5]
        
    experience = profile.get("work_experience", [])
    latest_role = experience[0].get("title", "Unknown") if experience else "Unknown"
    
    prompt = f"""You are an expert career advisor. Based on the candidate's verified skills and experience, suggest exactly 3 different job titles they should search for.

LATEST ROLE: {latest_role}
VERIFIED STRONG SKILLS: {', '.join(strong_skills)}

Guidelines:
1. Provide standard industry job titles (e.g., "Frontend Developer", "Data Engineer").
2. INFER SENIORITY: Look at their LATEST ROLE. If they are a "Senior", "Lead", or "Manager", include that seniority prefix in the suggested titles (e.g., "Senior Backend Developer"). If junior/fresher, leave it as the base title.
3. Don't be too narrow ("Python FastAPI Developer"), but don't be too broad ("Engineer").
4. Make them distinct but highly relevant to the skills.

Return ONLY a JSON array of strings, like: ["Title 1", "Title 2", "Title 3"]
"""
    return prompt


from langchain_core.runnables import RunnableConfig

async def suggest_titles_node(state: JobSearchState, config: RunnableConfig) -> dict:
    """Generate 3 job title suggestions using the LLM."""
    profile = state.get("user_profile", {})
    if not profile:
        return {"status": "error", "errors": ["No user profile provided."]}
        
    print(f"Generating job title suggestions based on verified profile...")
    
    prompt = _build_title_suggestion_prompt(profile)
    messages = [
        SystemMessage(content="You are a career advisor. Reply ONLY with a valid JSON array of 3 strings. No markdown formatting or explanations."),
        HumanMessage(content=prompt),
    ]
    
    # Extract BYOK Config
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    custom_model = configurable.get("custom_model")
    
    try:
        result = await call_llm_with_fallback(
            messages, 
            label="Title Suggestion",
            custom_api_key=custom_api_key,
            custom_model=custom_model
        )
        titles = result["data"]
        
        # Ensure it's a list of strings
        if not isinstance(titles, list) or len(titles) == 0:
            titles = ["Software Engineer", "Full Stack Developer", "Backend Developer"]
            
        # Limit to 3 just in case
        titles = titles[:3]
        
        print(f"   Suggested titles: {titles}")
        return {
            "suggested_titles": titles,
            "location": state.get("location", "India"),  # Default location
            "status": "titles_suggested"
        }
    except Exception as e:
        print(f"   Error suggesting titles: {str(e)}")
        return {
            "suggested_titles": ["Software Engineer", "Developer", "Engineer"], # Fallback
            "errors": [f"Failed to generate titles: {str(e)}"],
            "status": "titles_suggested_fallback"
        }


def select_titles_node(state: JobSearchState) -> dict:
    """HITL node where the user reviews/edits the suggested titles.
    
    The graph pauses BEFORE this node (using interrupt() in main.py, or we can use interrupt() here).
    Actually, we'll call interrupt() right inside this node.
    """
    suggested = state.get("suggested_titles", [])
    
    # Pause the graph and ask the user for input
    # The payload passed to interrupt() is what the UI/CLI sees
    interrupt_payload = {
        "message": "Please review and select job titles to search for.",
        "suggested_titles": suggested,
        "location": state.get("location", "India")
    }
    
    # The graph PAUSES here. It resumes when we call ainvoke(Command(resume=user_input))
    user_input = interrupt(interrupt_payload)
    
    # Parse the user's input (expected to be a dict with selected_titles and location)
    if isinstance(user_input, dict):
        selected = user_input.get("selected_titles", suggested)
        location = user_input.get("location", state.get("location", "India"))
    else:
        # Fallback if the user just sends a string or list
        selected = user_input if isinstance(user_input, list) else suggested
        location = state.get("location", "India")
        
    print(f"   User confirmed titles: {selected} (Location: {location})")
    
    return {
        "selected_titles": selected[:3], # Enforce max 3
        "location": location,
        "status": "titles_selected"
    }


# ═══════════════════════════════════════════════════════
# PARALLEL SEARCH PER TITLE
# ═══════════════════════════════════════════════════════

import asyncio

async def search_for_title_node(state: TitleSearchState) -> dict:
    """Search SerpAPI for a SINGLE title."""
    title = state["search_title"]
    location = state.get("location", "India")
    
    print(f"   Searching SerpAPI for '{title}' in {location}...")
    
    # Using 3 pages for SerpAPI
    all_jobs = await search_serpapi(title, location, max_pages=3)
            
    print(f"      Found {len(all_jobs)} jobs for '{title}'")
    
    # Only return the keys we want to merge into the parent state
    # Notice we don't return 'location' or 'search_title' to avoid concurrent update conflicts
    return {"job_listings": all_jobs}


# ═══════════════════════════════════════════════════════
# NODE 3: DEDUPLICATION (FAN-IN)
# ═══════════════════════════════════════════════════════

def deduplicate_and_rank_node(state: JobSearchState) -> dict:
    """Merge and deduplicate the list of jobs returned by all the parallel Send() branches."""
    all_jobs = state.get("job_listings", [])
    
    print(f"\nMerging results...")
    print(f"   Raw total: {len(all_jobs)} jobs across all pages and titles")
    
    # Deduplicate based on Title + Company (lowercased)
    unique_jobs = []
    seen_keys = set()
    
    for job in all_jobs:
        # Check if job is a dict or Pydantic model
        if isinstance(job, dict):
            title = job.get('title', '')
            company = job.get('company', '')
        else:
            title = job.title
            company = job.company
            
        # Create a normalization key
        title_norm = title.lower().strip()
        company_norm = company.lower().strip()
        key = f"{title_norm}::{company_norm}"
        
        if key not in seen_keys:
            seen_keys.add(key)
            if not isinstance(job, dict):
                job = job.model_dump()
            unique_jobs.append(job)
            
    unique_jobs.sort(key=lambda j: j.get('title', ''))
    
    print(f"   Deduplicated total: {len(unique_jobs)} unique jobs")
    
    return {
        "deduplicated_jobs": unique_jobs,
        "status": "search_complete"
    }


# ═══════════════════════════════════════════════════════
# ROUTING & MAIN GRAPH
# ═══════════════════════════════════════════════════════

def route_searches(state: JobSearchState):
    """The dynamic router that creates a Send() task for each selected title."""
    selected_titles = state.get("selected_titles", [])
    location = state.get("location", "India")
    
    sends = []
    for title in selected_titles:
        # Spawn a new parallel execution of the 'search_for_title' node
        sends.append(
            Send("search_for_title", {
                "search_title": title,
                "location": location
            })
        )
    return sends


def build_job_search_graph():
    """Build the main Job Search LangGraph."""
    graph = StateGraph(JobSearchState)
    
    # Add nodes
    graph.add_node("suggest_titles", suggest_titles_node)
    graph.add_node("select_titles", select_titles_node)
    graph.add_node("search_for_title", search_for_title_node)
    graph.add_node("deduplicate_and_rank", deduplicate_and_rank_node)
    
    # Edges
    graph.add_edge(START, "suggest_titles")
    graph.add_edge("suggest_titles", "select_titles")
    
    # Conditional edges for the fan-out
    graph.add_conditional_edges(
        "select_titles",
        route_searches,
        ["search_for_title"]  # The target node for the Send objects
    )
    
    # After all Send tasks complete, they fan-in to the dedup node
    graph.add_edge("search_for_title", "deduplicate_and_rank")
    graph.add_edge("deduplicate_and_rank", END)
    
    # MemorySaver required for the interrupt() in select_titles
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
