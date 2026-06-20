from pydantic import BaseModel, Field
from typing import List, Optional


class SkillRequirement(BaseModel):
    """A specific skill extracted from a job description."""
    name: str = Field(..., description="Normalized skill name (e.g., 'Python', 'Machine Learning')")
    level: str = Field(..., description="Required proficiency: 'beginner', 'intermediate', 'advanced', or 'unspecified'")
    is_mandatory: bool = Field(..., description="True if required, False if nice-to-have/bonus")


class JDRequirements(BaseModel):
    """Structured requirements extracted from a job description by the LLM."""
    required_skills: List[SkillRequirement] = Field(..., description="List of technical and soft skills required")
    experience_years_min: int = Field(0, description="Minimum years of experience required (0 if entry-level or not specified)")
    experience_years_max: Optional[int] = Field(None, description="Maximum years of experience mentioned (if any)")
    education: Optional[str] = Field(None, description="Required degree (e.g., 'Bachelors', 'Masters', 'PhD')")
    implicit_signals: List[str] = Field(..., description="Cultural or work environment signals (e.g., 'fast-paced', 'startup culture')")
    red_flags: List[str] = Field(..., description="Potential red flags (e.g., 'wear many hats', 'hustle', vague requirements)")
    ghost_probability: float = Field(0.0, description="LLM's heuristic estimation of whether this is a ghost job (0.0 to 1.0)")
    ghost_reasoning: str = Field("", description="Why the LLM assigned this ghost probability")
    extracted_salary: Optional[str] = Field(None, description="The salary or compensation range extracted directly from the JD text (if any)")
