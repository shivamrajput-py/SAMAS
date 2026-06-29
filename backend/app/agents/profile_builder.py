"""
Profile Builder Agent â€” The first agent in SAMAS's pipeline.

This is a LangGraph StateGraph with 4 nodes that form a linear pipeline:

    START â†’ extract_resume â†’ scrape_urls â†’ analyze_with_llm â†’ compute_scores â†’ END

Each node has one job:
    1. extract_resume:    Parse the PDF/DOCX file â†’ raw text (no LLM)
    2. scrape_urls:       Fetch GitHub/LinkedIn/portfolio pages â†’ raw content (no LLM)
    3. analyze_with_llm:  Send everything to the LLM â†’ structured extraction
    4. compute_scores:    Run our proof score formula â†’ final UserProfile (no LLM)

WHY THIS ORDER?
    We collect ALL data first (nodes 1 & 2), then analyze it all at once (node 3).
    This means one LLM call with full context, instead of multiple calls with
    partial information. Cheaper, faster, and the LLM can cross-reference
    the resume against external profiles in a single pass.

LANGGRAPH CONCEPTS USED:
    - StateGraph: Defines the graph structure (nodes + edges)
    - Nodes: Python functions that process state
    - Edges: Connections between nodes (linear in this agent)
    - Checkpointing: State is saved after each node, enabling resume-on-failure
    - Compile: Turns the graph definition into a runnable object
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.config import OPENROUTER_MODEL
from app.llm import call_llm_with_fallback, parse_llm_json_response, FALLBACK_MODELS
from app.agents.state import ProfileBuilderState
from app.models.user_profile import ResumeExtraction, UserProfile, ExtractionMetadata
from app.models.scoring import build_scored_skills
from app.tools.resume_parser import extract_resume_text
from app.tools.web_scraper import scrape_external_links


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 1: RESUME TEXT EXTRACTION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def extract_resume_node(state: ProfileBuilderState) -> dict:
    """Parse the resume PDF/DOCX and extract raw text.
    
    This node does NO LLM work â€” it's pure file parsing.
    pdfplumber handles PDFs, python-docx handles DOCX files.
    
    Why separate this from the LLM node?
        - Fail fast: if the file is corrupted, we know immediately
        - Clear responsibility: parsing â‰  understanding
        - Testable: we can unit test this without any LLM
    """
    file_path = state["resume_file_path"]
    filename = Path(file_path).name
    
    print(f"Extracting text from: {filename}")
    
    try:
        resume_text = extract_resume_text(file_path)
        print(f"   Extracted {len(resume_text)} characters from resume")
        
        return {
            "resume_text": resume_text,
            "resume_filename": filename,
            "status": "resume_extracted",
            "errors": [],
        }
    except Exception as e:
        error_msg = f"Failed to extract resume text: {str(e)}"
        print(f"   {error_msg}")
        return {
            "resume_text": "",
            "resume_filename": filename,
            "status": "resume_extraction_failed",
            "errors": [error_msg],
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 2: EXTERNAL URL SCRAPING
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def scrape_urls_node(state: ProfileBuilderState) -> dict:
    """Scrape all external URLs (GitHub, LinkedIn, portfolio).
    
    This node also does NO LLM work â€” it's HTTP requests.
    Uses Jina Reader for universal URLâ†’markdown conversion,
    and GitHub REST API for structured repo data.
    
    If any URL fails, we log the error but continue.
    External data is a bonus, not a requirement.
    """
    urls = state.get("external_urls", [])
    existing_errors = state.get("errors", [])
    
    if not urls:
        print("No external URLs provided â€” skipping scraping")
        return {
            "scraped_data": {},
            "status": "no_urls_provided",
            "errors": existing_errors,
        }
    
    print(f"Scraping {len(urls)} external link(s)...")
    for u in urls:
        print(f"   URL to scrape: '{u}'")
    
    scraped = await scrape_external_links(urls)
    
    # Log results for each URL with detail
    scrape_errors = []
    for url, data in scraped.items():
        if "error" in data:
            print(f"   FAILED {url}: {data['error']}")
            scrape_errors.append(f"Scraping failed for {url}: {data['error']}")
        else:
            data_type = data.get('type', 'unknown')
            has_api = bool(data.get('api_data'))
            has_page = bool(data.get('page_content'))
            page_len = len(data.get('page_content', '')) if has_page else 0
            print(f"   OK {url}: type={data_type}, has_api_data={has_api}, has_page_content={has_page} ({page_len} chars)")
            
            # For GitHub, show what we got
            if data_type == "github" and has_api:
                api = data["api_data"]
                if "error" not in api:
                    print(f"      GitHub: {api.get('public_repos', 0)} repos, languages: {api.get('languages', [])}")
                else:
                    print(f"      GitHub API error: {api['error']}")
            
            # For LinkedIn, show what we got
            if data_type == "linkedin" and has_api:
                api = data["api_data"]
                if "error" not in api:
                    print(f"      LinkedIn: {api.get('full_name', 'N/A')}, skills: {api.get('skills', [])[:5]}")
                else:
                    print(f"      LinkedIn API error: {api['error']}")
    
    return {
        "scraped_data": scraped,
        "status": "urls_scraped",
        "errors": existing_errors + scrape_errors,
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 3: LLM ANALYSIS (The one node that uses AI)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _build_extraction_prompt(resume_text: str, scraped_data: dict) -> str:
    """Build the prompt that tells the LLM what to extract.
    
    This is carefully structured to:
    1. Set clear expectations (granular skills, not broad languages)
    2. Provide the resume text
    3. Provide any external data we scraped
    4. Show the expected JSON output structure with an example
    
    The prompt is the most important piece for extraction quality.
    Small changes here have big impact on output quality.
    """
    
    prompt = """You are an expert resume analyzer. Your job is to extract ALL information from the provided resume text and any additional profile data into a structured JSON format.

CRITICAL RULES FOR SKILL EXTRACTION:
1. Extract GRANULAR, SPECIFIC skills â€” NOT broad programming languages:
   âœ… CORRECT: "FastAPI", "React", "PyTorch", "Docker", "Binary Trees", "Linear Algebra", "Transformers"
   WRONG: "Python", "JavaScript", "Machine Learning", "Web Development" (too vague â€” these are domains, not skills)
2. Programming languages should ONLY appear in the "parent_domain" field, never as the skill name itself
3. Extract skills from EVERY section: skills list, project descriptions, work experience descriptions
4. Include concepts and approaches: "CI/CD", "Microservices", "Event-Driven Architecture", "REST API"
5. Include math/science topics: "Linear Algebra", "Probability", "Bayesian Inference"
6. Include data structures and algorithms: "Binary Trees", "Dynamic Programming", "Graph Traversal"
7. Include specific tools and platforms: "AWS Lambda", "PostgreSQL", "Redis", "Kubernetes", "Docker Compose"

SKILL CATEGORY OPTIONS:
- "framework": React, FastAPI, Spring Boot, LangChain, Next.js
- "library": Pandas, NumPy, Scikit-learn, Lodash
- "tool": Docker, Git, Webpack, Postman, Figma
- "platform": AWS, GCP, Azure, Vercel, Heroku
- "database": PostgreSQL, MongoDB, Redis, DynamoDB
- "concept": Microservices, REST API, GraphQL, OAuth, WebSockets
- "algorithm": DFS, BFS, Dynamic Programming, Binary Search
- "data_structure": Binary Trees, Hash Maps, Graphs, Tries
- "math": Linear Algebra, Probability, Calculus, Statistics
- "methodology": Agile, Scrum, TDD, CI/CD
- "domain": NLP, Computer Vision, System Design, Data Engineering
- "language_feature": async/await, decorators, generics, closures
- "design_pattern": Observer, Factory, Singleton, MVC
- "other": anything that doesn't fit above

"""
    
    prompt += f"""
===== RESUME TEXT =====
{resume_text}
===== END RESUME TEXT =====
"""
    
    # Add scraped external data if available
    if scraped_data:
        has_external = False
        prompt += "\n===== EXTERNAL PROFILE DATA =====\n"
        prompt += "CRITICAL: You MUST extract skills from the following external profiles into github_skills, linkedin_skills, and portfolio_skills arrays respectively. Do NOT leave these empty if external data is present.\n\n"
        
        for url, data in scraped_data.items():
            if isinstance(data, dict) and "error" not in data:
                
                if data.get("type") == "github" and data.get("api_data"):
                    api = data["api_data"]
                    if "error" not in api:
                        has_external = True
                        prompt += f"\n--- GitHub Profile ({url}) ---\n"
                        prompt += f"Username: {api.get('username', 'N/A')}\n"
                        prompt += f"Bio: {api.get('bio', 'N/A')}\n"
                        prompt += f"Public repos: {api.get('public_repos', 0)}\n"
                        prompt += f"Languages used: {', '.join(api.get('languages', []))}\n"
                        prompt += "Repositories:\n"
                        for repo in api.get("repositories", []):
                            prompt += f"  - {repo['name']}: {repo.get('description', 'No description')}"
                            prompt += f" | Language: {repo.get('language', 'N/A')}"
                            topics = repo.get("topics", [])
                            if topics:
                                prompt += f" | Topics: {', '.join(topics)}"
                            prompt += "\n"
                        prompt += "\nINSTRUCTION: Extract ALL programming languages, frameworks, and tools visible in the GitHub repos above into the 'github_skills' array.\n"
                
                elif data.get("type") == "linkedin" and data.get("api_data"):
                    api = data["api_data"]
                    if "error" not in api:
                        has_external = True
                        prompt += f"\n--- LinkedIn Profile ({url}) ---\n"
                        prompt += f"Name: {api.get('full_name', api.get('firstName', 'N/A'))}\n"
                        prompt += f"Headline: {api.get('headline', 'N/A')}\n"
                        prompt += f"Summary: {api.get('summary', api.get('about', 'N/A'))}\n"
                        
                        li_skills = api.get('skills', [])
                        if li_skills:
                            prompt += f"Skills: {', '.join(li_skills)}\n"
                        
                        for exp in api.get('experiences', api.get('positions', [])):
                            if isinstance(exp, dict):
                                title = exp.get('title', exp.get('position', ''))
                                company = exp.get('company', exp.get('companyName', ''))
                                desc = exp.get('description', '')
                                prompt += f"  - {title} at {company}\n"
                                if desc:
                                    prompt += f"    {desc[:500]}\n"
                        
                        prompt += "\nINSTRUCTION: Extract ALL skills from the LinkedIn profile above into the 'linkedin_skills' array.\n"
                
                if data.get("page_content"):
                    label = data.get("type", "external").title()
                    page_text = data["page_content"]
                    if len(page_text) > 2000:
                        page_text = page_text[:2000] + "\n[... truncated ...]\n"
                    prompt += f"\n--- {label} Page Content ({url}) ---\n"
                    prompt += page_text
                    prompt += "\n"
                    has_external = True
        
        if not has_external:
            prompt += "(No external data was successfully scraped)\n"
        
        prompt += "===== END EXTERNAL DATA =====\n"
    
    # The output format specification with a partial example
    prompt += """

Now extract ALL information into the following JSON structure. 

IMPORTANT:
- For skills_listed: extract EVERY granular skill from the resume's skills section
- For skills_used (in work experience) and technologies_used (in projects): list skill names as strings
- For github_skills, portfolio_skills, linkedin_skills: list any additional skills found in external sources
- Include ALL fields even if empty (use empty arrays [] or null)
- Your response must be ONLY valid JSON â€” no explanations, no markdown formatting, no code blocks

{
  "personal_info": {
    "full_name": "...",
    "email": "..." or null,
    "phone": "..." or null,
    "city": "..." or null,
    "state": "..." or null,
    "country": "..." or null,
    "linkedin_url": "..." or null,
    "github_url": "..." or null,
    "portfolio_url": "..." or null,
    "other_urls": [],
    "professional_summary": "..." or null
  },
  "education": [
    {
      "institution": "...",
      "degree": "...",
      "field_of_study": "...",
      "start_date": "..." or null,
      "end_date": "..." or null,
      "is_current": false,
      "gpa": "..." or null,
      "relevant_coursework": [],
      "achievements": []
    }
  ],
  "work_experience": [
    {
      "company": "...",
      "title": "...",
      "location": "..." or null,
      "start_date": "..." or null,
      "end_date": "..." or null,
      "is_current": false,
      "description": "...",
      "responsibilities": [],
      "skills_used": ["FastAPI", "PostgreSQL", "Docker"]
    }
  ],
  "projects": [
    {
      "name": "...",
      "description": "...",
      "url": null,
      "github_url": null,
      "technologies_used": ["Next.js", "Tailwind CSS", "Supabase"],
      "role": null,
      "key_achievements": []
    }
  ],
  "skills_listed": [
    {"name": "FastAPI", "category": "framework", "parent_domain": "Python"},
    {"name": "React", "category": "framework", "parent_domain": "JavaScript"},
    {"name": "Binary Trees", "category": "data_structure", "parent_domain": "DSA"},
    {"name": "Linear Algebra", "category": "math", "parent_domain": "Mathematics"}
  ],
  "certifications": [],
  "publications": [],
  "achievements": [
    {
      "title": "...",
      "issuer": "..." or null,
      "date": "..." or null,
      "description": "..." or null
    }
  ],
  "volunteer_experience": [],
  "spoken_languages": [],
  "interests": [],
  "github_skills": [],
  "portfolio_skills": [],
  "linkedin_skills": []
}"""
    
    return prompt



from langchain_core.runnables import RunnableConfig

async def analyze_with_llm_node(state: ProfileBuilderState, config: RunnableConfig) -> dict:
    """Send all collected data to the LLM for structured extraction.
    
    This is the ONE node in the pipeline that uses an LLM.
    It receives:
    - Raw resume text (from node 1)
    - Scraped external data (from node 2)
    
    And produces:
    - A structured ResumeExtraction (validated by Pydantic)
    """
    resume_text = state.get("resume_text", "")
    scraped_data = state.get("scraped_data", {})
    existing_errors = state.get("errors", [])
    
    if not resume_text:
        return {
            "raw_extraction": {},
            "status": "skipped_llm_no_resume_text",
            "errors": existing_errors + ["No resume text available for LLM analysis"],
        }
    
    print("Sending data to LLM for structured extraction...")
    
    prompt = _build_extraction_prompt(resume_text, scraped_data)
    
    messages = [
        SystemMessage(content=(
            "You are an expert resume parser. Extract structured information "
            "from resumes accurately and completely. Always respond with valid JSON only."
        )),
        HumanMessage(content=prompt),
    ]
    
    # Extract BYOK Config
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    custom_model = configurable.get("custom_model")
    
    try:
        # call_llm_with_fallback handles model rotation, retries, and JSON parsing.
        result = await call_llm_with_fallback(
            messages, 
            label="Resume Extractor",
            custom_api_key=custom_api_key,
            custom_model=custom_model,
            config=config
        )
        parsed_json = result["data"]
        successful_model = result["model_used"]
        
        # Strictly validate the extracted schema
        extraction = ResumeExtraction.model_validate(parsed_json)
        
        skills_count = len(extraction.skills_listed)
        exp_count = len(extraction.work_experience)
        proj_count = len(extraction.projects)
        print(f"   Extracted: {skills_count} skills, {exp_count} experiences, {proj_count} projects")
        if successful_model != OPENROUTER_MODEL and not custom_model:
            print(f"    Used fallback model: {successful_model}")
        
        return {
            "raw_extraction": extraction.model_dump(),
            "status": "llm_analysis_complete",
            "errors": existing_errors,
            "llm_model_used": successful_model,
        }
    except RuntimeError as e:
        # All models failed
        error_msg = str(e)
        print(f"   {error_msg}")
        return {
            "raw_extraction": {},
            "status": "all_models_failed",
            "errors": existing_errors + [error_msg],
        }
    except Exception as e:
        error_msg = f"Extraction/validation failed: {str(e)}"
        print(f"   {error_msg}")
        return {
            "raw_extraction": {},
            "status": "llm_analysis_failed",
            "errors": existing_errors + [error_msg],
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 4: PROOF SCORE COMPUTATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def compute_scores_node(state: ProfileBuilderState) -> dict:
    """Compute proof scores and build the final UserProfile.
    
    This node does NO LLM work â€” it's pure Python math.
    
    It takes the raw extraction from the LLM and:
    1. Collects all skill mentions from every source
    2. Deduplicates skills by normalized name
    3. Computes proof scores using our evidence-tiering formula
    4. Builds the final UserProfile with metadata
    
    Why is scoring in Python instead of the LLM?
        - LLMs are bad at consistent math
        - Our formula is deterministic â€” same evidence = same score every time
        - Easier to debug and adjust weights
        - No additional API cost
    """
    raw_extraction = state.get("raw_extraction", {})
    existing_errors = state.get("errors", [])
    
    if not raw_extraction:
        return {
            "user_profile": {},
            "status": "skipped_scoring_no_extraction",
            "errors": existing_errors + ["No extraction data available for scoring"],
        }
    
    print("Computing proof scores...")
    
    try:
        # Reconstruct the Pydantic model from the dict
        extraction = ResumeExtraction.model_validate(raw_extraction)
        
        # Run the scoring algorithm (this is where the magic happens)
        scored_skills = build_scored_skills(extraction)
        
        # Calculate metadata
        scores = [s.proof_score for s in scored_skills]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Score distribution for the metadata
        distribution = {"Low": 0, "Medium": 0, "High": 0, "Very High": 0}
        for skill in scored_skills:
            distribution[skill.confidence_label] += 1
        
        # Determine which URLs were successfully scraped
        scraped_data = state.get("scraped_data", {})
        successful_urls = [
            url for url, data in scraped_data.items()
            if isinstance(data, dict) and "error" not in data
        ]
        
        # Build the final UserProfile
        profile = UserProfile(
            personal_info=extraction.personal_info,
            education=extraction.education,
            work_experience=extraction.work_experience,
            projects=extraction.projects,
            skills=scored_skills,
            certifications=extraction.certifications,
            publications=extraction.publications,
            achievements=extraction.achievements,
            volunteer_experience=extraction.volunteer_experience,
            spoken_languages=extraction.spoken_languages,
            interests=extraction.interests,
            extraction_metadata=ExtractionMetadata(
                resume_filename=state.get("resume_filename", "unknown"),
                external_urls_scraped=successful_urls,
                extraction_timestamp=datetime.now(timezone.utc).isoformat(),
                llm_model_used=state.get("llm_model_used", OPENROUTER_MODEL),
                total_skills_extracted=len(scored_skills),
                average_proof_score=round(avg_score, 2),
                score_distribution=distribution,
            ),
        )
        
        # Print a summary
        print(f"   {len(scored_skills)} skills scored")
        print(f"   Average proof score: {avg_score:.2f}")
        print(f"   Distribution: {distribution}")
        
        return {
            "user_profile": profile.model_dump(),
            "status": "complete",
            "errors": existing_errors,
        }
        
    except Exception as e:
        error_msg = f"Scoring failed: {str(e)}"
        print(f"   {error_msg}")
        return {
            "user_profile": {},
            "status": "scoring_failed",
            "errors": existing_errors + [error_msg],
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GRAPH DEFINITION â€” Wiring the nodes together
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def build_profile_builder_graph():
    """Build and compile the Profile Builder agent's LangGraph.
    
    The graph is a simple linear pipeline:
        START â†’ extract_resume â†’ scrape_urls â†’ analyze_with_llm â†’ compute_scores â†’ END
    
    LangGraph concepts in play:
    - StateGraph: Manages the shared state across all nodes
    - add_node: Registers a function as a processing step
    - add_edge: Connects nodes in sequence
    - START/END: Special constants for entry/exit points
    - MemorySaver: In-memory checkpointing (saves state after each node)
    
    The MemorySaver checkpointer means that if the pipeline crashes at
    node 3, we could potentially resume from node 2's output without
    re-parsing the resume or re-scraping URLs. For production, we'd
    swap this for PostgresSaver to persist across server restarts.
    
    Returns:
        A compiled LangGraph runnable that accepts ProfileBuilderState
    """
    # Create the graph with our state schema
    graph = StateGraph(ProfileBuilderState)
    
    # Register all four nodes
    graph.add_node("extract_resume", extract_resume_node)
    graph.add_node("scrape_urls", scrape_urls_node)
    graph.add_node("analyze_with_llm", analyze_with_llm_node)
    graph.add_node("compute_scores", compute_scores_node)
    
    # Wire them in sequence: START â†’ 1 â†’ 2 â†’ 3 â†’ 4 â†’ END
    graph.add_edge(START, "extract_resume")
    graph.add_edge("extract_resume", "scrape_urls")
    graph.add_edge("scrape_urls", "analyze_with_llm")
    graph.add_edge("analyze_with_llm", "compute_scores")
    graph.add_edge("compute_scores", END)
    
    # Compile with in-memory checkpointing
    # In production, replace MemorySaver with PostgresSaver for persistence
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    return compiled_graph
