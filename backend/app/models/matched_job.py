from pydantic import BaseModel, Field
from typing import List
from app.models.job import JobListing
from app.models.jd_requirements import JDRequirements


class MatchedJob(BaseModel):
    """A job listing that has been scored against the user's profile."""
    
    job: JobListing
    jd_requirements: JDRequirements
    
    # Mathematical scores
    match_score: float = Field(..., description="Overall match score (0.0 to 1.0)")
    skill_overlap_score: float = Field(..., description="Component: % of required skills matched, weighted by proof")
    experience_delta_score: float = Field(..., description="Component: Proximity of user's years of experience to requirement")
    embedding_similarity: float = Field(..., description="Component: Cosine similarity of profile vs JD text")
    proof_alignment_score: float = Field(..., description="Component: Average proof score of matched skills")
    
    # Classification
    tier: str = Field(..., description="'easy_get', 'best_match', 'stretch_goal', or 'filtered'")
    
    # Skill Gap Analysis
    matched_skills: List[str] = Field(..., description="Skills the user HAS that the job needs")
    missing_skills: List[str] = Field(..., description="Skills the user LACKS that the job needs")
    skill_gap_summary: str = Field(..., description="Brief summary of the gap (e.g., 'You need to learn X and Y')")
