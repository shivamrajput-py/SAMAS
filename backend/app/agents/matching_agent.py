import json
import numpy as np
from typing import List, Dict, TypedDict

# LangChain / LangGraph
from langgraph.graph import StateGraph, START, END

# Local
from app.models.job import JobListing
from app.models.jd_requirements import JDRequirements
from app.models.matched_job import MatchedJob

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import os

_EMBEDDER = None

class MatchingState(TypedDict):
    """Main state for the Matching & Ranking Agent."""
    unique_jobs: List[JobListing]
    extracted_requirements: Dict[str, dict]
    user_profile: dict
    
    # Results
    matched_jobs: List[MatchedJob]


from langchain_core.runnables import RunnableConfig

def _get_embedder(custom_api_key: str = None):
    global _EMBEDDER
    if custom_api_key:
        print("   Loading embedding model with custom BYOK key...")
        return OpenAIEmbeddings(
            openai_api_base=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openai_api_key=custom_api_key,
            model="openai/text-embedding-3-small"
        )
        
    if _EMBEDDER is None:
        _EMBEDDER = OpenAIEmbeddings(
            openai_api_base=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openai_api_key=os.environ.get("OPENROUTER_API_KEY"),
            model="openai/text-embedding-3-small"
        )
    return _EMBEDDER

# ═══════════════════════════════════════════════════════
# MATH SCORING ENGINE
# ═══════════════════════════════════════════════════════

def _calculate_experience_years(profile: dict) -> float:
    """Calculate total years of experience from the user's work history.
    
    Parses start_date and end_date from each work experience entry.
    Handles various formats: 'Aug 2024', '2024', 'Jan 2023 - Present', etc.
    Falls back to 1.0 if dates are unparseable (safer than 0).
    """
    from datetime import datetime
    import re
    
    experiences = profile.get("work_experience", [])
    if not experiences:
        return 0.0
    
    total_months = 0
    
    for exp in experiences:
        start_raw = exp.get("start_date", "")
        end_raw = exp.get("end_date", "")
        is_current = exp.get("is_current", False)
        
        if not start_raw:
            continue
        
        # Parse a date string into a (year, month) tuple
        def _parse_date(s: str):
            if not s:
                return None
            s = s.strip()
            
            # "Present" or "Current"
            if s.lower() in ("present", "current", "now"):
                now = datetime.now()
                return (now.year, now.month)
            
            # Try "Aug 2024", "August 2024", "Dec 2023"
            for fmt in ("%b %Y", "%B %Y", "%m/%Y", "%Y-%m"):
                try:
                    dt = datetime.strptime(s, fmt)
                    return (dt.year, dt.month)
                except ValueError:
                    continue
            
            # Try just a year: "2024"
            year_match = re.search(r'(\d{4})', s)
            if year_match:
                return (int(year_match.group(1)), 6)  # Assume mid-year
            
            return None
        
        start = _parse_date(start_raw)
        
        if is_current or (end_raw and end_raw.strip().lower() in ("present", "current", "now")):
            now = datetime.now()
            end = (now.year, now.month)
        else:
            end = _parse_date(end_raw)
        
        if start and end:
            months = (end[0] - start[0]) * 12 + (end[1] - start[1])
            if months > 0:
                total_months += months
    
    years = total_months / 12.0
    
    # Sanity: if parsing failed for everything, return a safe default
    if years == 0.0 and len(experiences) > 0:
        return 1.0  # At least they have SOME experience listed
    
    return round(years, 1)


def score_jobs_node(state: MatchingState, config: RunnableConfig) -> dict:
    jobs = state.get("unique_jobs", [])
    extracted = state.get("extracted_requirements", {})
    profile = state.get("user_profile", {})
    
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    
    print(f"\n[Matching Agent] Step 1: Running Math Scoring Engine")
    
    # 1. Prepare user profile data
    user_skills_dict = {}
    for skill in profile.get("skills", []):
        user_skills_dict[skill["name"].lower()] = skill.get("proof_score", 0.5)
            
    user_years = _calculate_experience_years(profile)
    
    # 2. Get profile embedding & query Pinecone
    try:
        embedder = _get_embedder(custom_api_key=custom_api_key)
        profile_text = f"Professional Summary: {profile.get('personal_info', {}).get('professional_summary', '')} Skills: {', '.join(user_skills_dict.keys())}"
        
        index_name = os.environ.get("PINECONE_INDEX_NAME", "samas-index")
        vectorstore = PineconeVectorStore(index_name=index_name, embedding=embedder)
        
        # Search all
        results = vectorstore.similarity_search_with_score(profile_text, k=len(jobs) if jobs else 100)
        
        # results is a list of (Document, score) tuples.
        # Map job_id metadata to score
        sim_scores = {doc.metadata.get("job_id"): score for doc, score in results if doc.metadata.get("job_id")}
        
    except Exception as e:
        print(f"   Pinecone Error: {e}. Falling back to 0.5 embedding score.")
        sim_scores = {j.id: 0.5 for j in jobs}
        
        
    matched_results = []
    
    for job in jobs:
        reqs_dict = extracted.get(job.id, {})
        reqs = JDRequirements(**reqs_dict) if reqs_dict else JDRequirements(required_skills=[], implicit_signals=[], red_flags=[])
        
        # --- COMPONENT 1: Skill Overlap (35%) ---
        matched_skills = []
        missing_skills = []
        overlap_score = 0.0
        
        if reqs.required_skills:
            for s in reqs.required_skills:
                s_name = s.name.lower()
                # Fuzzy match: is the required skill in the user's skill names?
                found = False
                for u_skill in user_skills_dict.keys():
                    if s_name in u_skill or u_skill in s_name:
                        matched_skills.append(s.name)
                        found = True
                        break
                if not found:
                    missing_skills.append(s.name)
            
            overlap_score = len(matched_skills) / len(reqs.required_skills)
        else:
            # Snippet jobs without extracted skills
            overlap_score = 0.5 
            
        # --- COMPONENT 2: Experience Delta (20%) ---
        exp_delta_score = 0.5 # Default neutral
        if reqs.experience_years_min > 0:
            delta = abs(user_years - reqs.experience_years_min)
            # Decays linearly: 0 diff = 1.0, 5 diff = 0.0
            exp_delta_score = max(0.0, 1.0 - (delta / 5.0))
            
        # --- COMPONENT 3: Embedding Similarity (25%) ---
        # Normalize FAISS output (which can sometimes be > 1.0 due to float math) to 0-1
        emb_sim = max(0.0, min(1.0, sim_scores.get(job.id, 0.5)))
        
        # --- COMPONENT 4: Proof Alignment (20%) ---
        proof_alignment_score = 0.5
        if matched_skills:
            proofs = []
            for s in matched_skills:
                for u_skill, p_score in user_skills_dict.items():
                    if s.lower() in u_skill or u_skill in s.lower():
                        proofs.append(p_score)
                        break
            if proofs:
                proof_alignment_score = sum(proofs) / len(proofs)
                
                
        # --- FINAL MATH ---
        # match_score = skill_overlap_score * 0.35 + experience_delta_score * 0.20 + embedding_similarity * 0.25 + proof_alignment_score * 0.20
        # Wait, if description_quality == "snippet", adjust weights
        if job.description_quality == "snippet":
            match_score = (emb_sim * 0.60) + (overlap_score * 0.40) # Rely mostly on embeddings for snippets
        else:
            match_score = (
                overlap_score * 0.35 +
                exp_delta_score * 0.20 +
                emb_sim * 0.25 +
                proof_alignment_score * 0.20
            )
            
        # --- TIER CLASSIFICATION ---
        tier = "filtered"
        if reqs.ghost_probability > 0.70:
            tier = "ghost"
        elif match_score > 0.80:
            tier = "easy_get"
        elif match_score > 0.55:
            tier = "best_match"
        elif match_score > 0.30:
            tier = "stretch_goal"
            
        if len(missing_skills) == 0:
            gap_summary = "You meet all extracted technical requirements."
        elif len(missing_skills) <= 2:
            gap_summary = f"You're very close. Brush up on: {', '.join(missing_skills)}."
        else:
            gap_summary = f"Significant gap. Missing: {', '.join(missing_skills[:3])} and others."
            
        matched_results.append(
            MatchedJob(
                job=job,
                jd_requirements=reqs,
                match_score=match_score,
                skill_overlap_score=overlap_score,
                experience_delta_score=exp_delta_score,
                embedding_similarity=emb_sim,
                proof_alignment_score=proof_alignment_score,
                tier=tier,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
                skill_gap_summary=gap_summary
            )
        )
        
    # Sort by score descending
    matched_results.sort(key=lambda x: x.match_score, reverse=True)
    
    print(f"   Scored and bucketed {len(matched_results)} jobs")
    return {"matched_jobs": matched_results}


# ═══════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════

def build_matching_graph() -> StateGraph:
    builder = StateGraph(MatchingState)
    builder.add_node("score_jobs", score_jobs_node)
    builder.add_edge(START, "score_jobs")
    builder.add_edge("score_jobs", END)
    return builder.compile()
