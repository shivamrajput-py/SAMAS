from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class JobListing(BaseModel):
    """One job from any source, normalized into a common format."""
    
    id: str = Field(..., description="Unique ID for this listing (usually a hash of title+company+source)")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location (e.g., 'Remote', 'New Delhi, India')")
    description: str = Field(..., description="Full or partial job description/snippet")
    description_quality: str = Field(default="full_text", description="'full_text', 'snippet', or 'html'")
    url: str = Field(..., description="URL to apply or view the job")
    
    # Optional fields that might not be provided by every source
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    job_type: Optional[str] = Field(None, description="full-time, contract, remote, etc.")
    posted_date: Optional[str] = Field(None, description="ISO date string or human readable '2 days ago'")
    
    # Metadata for our system
    source: str = Field(..., description="'serpapi', 'linkedin', etc.")
    search_title: str = Field(..., description="Which generated title search found this job")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Internal metadata like drop_reason")
