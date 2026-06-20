"""
LangGraph State Definition — The shared memory of the Profile Builder agent.

In LangGraph, State is a TypedDict that flows through every node in the graph.
Each node reads from the state, does its work, and writes updates back.
Think of it as a shared clipboard that every team member can read and write to.

HOW STATE WORKS IN LANGGRAPH:
    1. You define a TypedDict with all fields your graph needs
    2. The graph starts with initial values (user input)
    3. Each node returns a dict with ONLY the fields it wants to update
    4. LangGraph merges those updates into the shared state
    5. The next node sees the updated state
    
    Example flow:
        Initial state: {resume_file_path: "resume.pdf", resume_text: ""}
        → extract_resume node runs, returns {"resume_text": "John Doe..."}
        → State is now: {resume_file_path: "resume.pdf", resume_text: "John Doe..."}
        → scrape_urls node sees the updated state and does its thing

WHY TypedDict AND NOT A PYDANTIC MODEL?
    LangGraph specifically requires TypedDict for state definitions.
    This is because LangGraph needs to merge partial updates efficiently,
    and TypedDict's simplicity makes this reliable. Pydantic models would
    add validation overhead on every state update, which is unnecessary
    since our actual data validation happens in the schemas (user_profile.py).
"""

from typing import TypedDict, List


class ProfileBuilderState(TypedDict, total=False):
    """Shared state for the Profile Builder agent's LangGraph.
    
    total=False means all fields are optional. This is important because
    nodes return partial updates — a node that extracts resume text only
    returns {"resume_text": "..."}, not the entire state.
    
    The fields are ordered by the pipeline stage where they get populated:
    
    Stage 0 (Input):     resume_file_path, external_urls
    Stage 1 (Extract):   resume_text, resume_filename
    Stage 2 (Scrape):    scraped_data
    Stage 3 (Analyze):   raw_extraction
    Stage 4 (Score):     user_profile
    Throughout:          status, errors
    """
    
    # ─── Stage 0: User Input ─────────────────────────
    # These are provided when the graph is first invoked.
    
    resume_file_path: str          # Path to the resume PDF/DOCX file
    external_urls: List[str]       # GitHub, LinkedIn, portfolio URLs
    
    # ─── Stage 1: Resume Extraction ──────────────────
    # Populated by the extract_resume node (no LLM, just parsing)
    
    resume_text: str               # Raw text extracted from the resume
    resume_filename: str           # Original filename for metadata
    
    # ─── Stage 2: Web Scraping ───────────────────────
    # Populated by the scrape_urls node (no LLM, just HTTP requests)
    
    scraped_data: dict             # URL -> scraped content dict
    
    # ─── Stage 3: LLM Analysis ──────────────────────
    # Populated by the analyze_with_llm node
    # This is the raw LLM output as a dict (before proof scoring)
    
    raw_extraction: dict           # ResumeExtraction.model_dump()
    llm_model_used: str            # Which model actually succeeded (may differ from .env if fallback was used)
    
    # ─── Stage 4: Final Output ──────────────────────
    # Populated by the compute_scores node (no LLM, just our formula)
    
    user_profile: dict             # UserProfile.model_dump()
    
    # ─── Status Tracking ────────────────────────────
    # Updated by every node so we can track progress
    
    status: str                    # Current status message
    errors: List[str]              # Any non-fatal errors that occurred
