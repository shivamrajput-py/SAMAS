import re
from datetime import datetime, timedelta
from app.models.job import JobListing
from app.models.jd_requirements import JDRequirements

def calculate_ghost_probability(
    job: JobListing, 
    jd: JDRequirements, 
    similar_company_jobs_count: int,
    llm_base_prob: float
) -> float:
    """
    Calculate the probability that this is a ghost job based on 5 heuristic signals.
    """
    signals = []
    prob = 0.0
    
    # Signal 1: Posting age > 30 days (High: 0.30)
    posted_at = job.posted_date or ""
    if "30 days ago" in posted_at or "month ago" in posted_at:
        prob += 0.30
        signals.append("Posted > 30 days ago")
        
    # Signal 2: Vague requirements (Medium: 0.20)
    # If the LLM extracted fewer than 3 specific skills, it's very vague
    if len(jd.required_skills) < 3:
        prob += 0.20
        signals.append(f"Vague requirements (only {len(jd.required_skills)} skills specified)")
        
    # Signal 3: "Competitive salary" without range (Low: 0.10)
    # SerpAPI doesn't have a structured salary field right now, so we check description
    desc_lower = job.description.lower()
    if "competitive salary" in desc_lower and "$" not in desc_lower and "₹" not in desc_lower:
        prob += 0.10
        signals.append("Claims 'competitive salary' with no numeric range")
        
    # Signal 4: Same company posting 3+ similar roles (Medium: 0.20)
    if similar_company_jobs_count >= 2: # means 3+ including itself
        prob += 0.20
        signals.append(f"Company has {similar_company_jobs_count + 1} very similar roles posted")
        
    # Combine with LLM's own estimation (Max 0.20 influence from LLM's raw instinct)
    # The LLM reads the implicitly vague tone or "pipeline building" language
    llm_contrib = min(0.20, llm_base_prob * 0.20)
    prob += llm_contrib
    if llm_contrib > 0.05:
        signals.append(f"LLM flagged tone/language as suspicious ({jd.ghost_reasoning})")
        
    # Cap at 1.0
    final_prob = min(1.0, prob)
    
    return final_prob, signals
