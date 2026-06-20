"""
Data models for SAMAS.

- user_profile.py â†’ Pydantic schemas for resume extraction and final user profile
- scoring.py      â†’ Proof score computation logic (the formula)
"""

from app.models.user_profile import (
    ResumeExtraction,
    UserProfile,
    ScoredSkill,
    ExtractedSkillEntry,
    SkillCategory,
    EvidenceType,
)
from app.models.scoring import compute_proof_score, build_scored_skills
