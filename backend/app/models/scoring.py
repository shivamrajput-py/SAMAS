"""
Proof Score Computation â€” The math behind SAMAS's skill assessment.

This module takes the raw extraction from the LLM and computes
proof scores for each skill using our evidence-tiering formula.

THE FORMULA:
    proof_score = min(1.0, resume_evidence + external_evidence)

    resume_evidence  = max score from within-resume sources (no double counting)
    external_evidence = sum of bonuses from independent external sources

WHY THIS WORKS:
    The problem with a simple weighted average: if someone lists "React" in
    their skills section AND describes a React project, they'd get credit twice
    from the same source (their resume). That's double-counting self-reported data.
    
    Our fix: everything in the resume is ONE bucket. We take the STRONGEST
    signal from within the resume (max, not sum). Then external sources
    (GitHub, portfolio, certifications) add independent corroboration on top.

EXAMPLE SCORES:
    Skill only in skills section          â†’ 0.25 (just a claim)
    Skill in project description          â†’ 0.40 (demonstrated in context)
    Skill in experience description       â†’ 0.50 (used professionally)
    Skill in project + experience         â†’ 0.55 (multiple professional contexts)
    Skill in project + GitHub             â†’ 0.40 + 0.20 = 0.60 (external corroboration)
    Skill in experience + GitHub + cert   â†’ 0.50 + 0.20 + 0.10 = 0.80 (strong evidence)
"""

from typing import List, Set, Dict, Optional
from app.models.user_profile import (
    ResumeExtraction,
    ScoredSkill,
    SkillEvidence,
    SkillCategory,
    EvidenceType,
    ExtractedSkillEntry,
)


# â”€â”€â”€ Score weights for each evidence source â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are carefully tuned: resume sources represent self-reported claims
# (lower base value), external sources represent independent verification.

RESUME_EVIDENCE_WEIGHTS = {
    EvidenceType.RESUME_SKILLS_SECTION: 0.25,    # Weakest: anyone can type it
    EvidenceType.RESUME_PROJECT: 0.40,           # Medium: described in context
    EvidenceType.RESUME_EXPERIENCE: 0.50,        # Stronger: used professionally
}

# Bonus when a skill appears in BOTH project AND experience within resume.
# This is the only case where within-resume evidence compounds,
# because having used something in a personal project AND at work
# is genuinely stronger than either alone.
RESUME_COMBINED_PROJECT_AND_EXPERIENCE = 0.55

EXTERNAL_EVIDENCE_BONUSES = {
    EvidenceType.GITHUB: 0.20,          # Strong: code exists publicly
    EvidenceType.PORTFOLIO: 0.10,       # Medium: showcased on portfolio
    EvidenceType.LINKEDIN: 0.10,        # Medium: professional profile
    EvidenceType.CERTIFICATION: 0.10,   # Medium: passed an exam
}


def compute_proof_score(evidence_types: Set[EvidenceType]) -> float:
    """Compute the proof score for a single skill based on its evidence sources.
    
    This implements the evidence-tiering model:
    1. From resume sources: take the MAX (no double counting)
    2. From external sources: SUM the bonuses (independent corroboration)
    3. Cap at 1.0
    
    Args:
        evidence_types: Set of EvidenceType values where this skill was found
        
    Returns:
        Float between 0.0 and 1.0
    """
    if not evidence_types:
        return 0.0
    
    # Step 1: Resume evidence â€” take the strongest signal only
    resume_types = {et for et in evidence_types if et.value.startswith("resume_")}
    
    if resume_types:
        # Check for the combined project + experience bonus
        has_project = EvidenceType.RESUME_PROJECT in resume_types
        has_experience = EvidenceType.RESUME_EXPERIENCE in resume_types
        
        if has_project and has_experience:
            resume_score = RESUME_COMBINED_PROJECT_AND_EXPERIENCE
        else:
            # Take the max individual weight
            resume_score = max(
                RESUME_EVIDENCE_WEIGHTS.get(et, 0.0) for et in resume_types
            )
    else:
        resume_score = 0.0
    
    # Step 2: External evidence â€” sum all applicable bonuses
    external_types = evidence_types - resume_types
    external_score = sum(
        EXTERNAL_EVIDENCE_BONUSES.get(et, 0.0) for et in external_types
    )
    
    # Step 3: Cap at 1.0
    return min(1.0, resume_score + external_score)


def get_confidence_label(score: float) -> str:
    """Convert a numeric proof score into a human-readable label.
    
    These labels appear in the UI next to each skill.
    The thresholds are chosen to be meaningful:
    - Low: just a claim, no supporting evidence
    - Medium: some context (mentioned in projects/experience)  
    - High: corroborated by external sources
    - Very High: strong multi-source evidence
    """
    if score >= 0.70:
        return "Very High"
    elif score >= 0.50:
        return "High"
    elif score >= 0.30:
        return "Medium"
    else:
        return "Low"


def _normalize_skill_name(name: str) -> str:
    """Normalize a skill name for deduplication.
    
    'React.js', 'ReactJS', 'React' should all be treated as the same skill.
    We lowercase and strip common suffixes, but keep the original casing
    for the display name.
    """
    normalized = name.strip().lower()
    # Remove common suffixes that cause false duplicates
    suffixes_to_strip = [".js", ".py", ".ts"]
    for suffix in suffixes_to_strip:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized


def build_scored_skills(extraction: ResumeExtraction) -> List[ScoredSkill]:
    """Build proof-scored skills from the raw LLM extraction.
    
    This is the core post-processing function. It:
    1. Collects every skill mention from every source in the extraction
    2. Deduplicates by normalized name
    3. Determines evidence sources for each unique skill
    4. Computes proof scores using our formula
    5. Returns sorted list (highest score first)
    
    Args:
        extraction: The raw LLM extraction containing all resume sections
        
    Returns:
        List of ScoredSkill objects sorted by proof_score descending
    """
    
    # This dict maps normalized_skill_name -> {
    #   "display_name": str,           (original casing for display)
    #   "category": SkillCategory,
    #   "parent_domain": str,
    #   "evidence": List[SkillEvidence],
    #   "evidence_types": Set[EvidenceType],
    # }
    skill_registry: Dict[str, dict] = {}
    
    def register_skill(
        name: str,
        evidence_type: EvidenceType,
        context: str,
        category: Optional[SkillCategory] = None,
        parent_domain: Optional[str] = None
    ):
        """Register a skill mention from any source.
        
        If we've seen this skill before, we add the new evidence.
        If it's new, we create an entry with whatever category info we have.
        """
        normalized = _normalize_skill_name(name)
        if not normalized:
            return
            
        if normalized not in skill_registry:
            skill_registry[normalized] = {
                "display_name": name.strip(),
                "category": category or SkillCategory.OTHER,
                "parent_domain": parent_domain or "General",
                "evidence": [],
                "evidence_types": set(),
            }
        
        entry = skill_registry[normalized]
        
        # If this new mention has better category info, use it.
        # The skills_listed entries have proper categories from the LLM;
        # skills found in experience/project descriptions might not.
        if category and category != SkillCategory.OTHER:
            entry["category"] = category
        if parent_domain and parent_domain != "General":
            entry["parent_domain"] = parent_domain
        
        # Add evidence (avoid exact duplicate entries)
        evidence_item = SkillEvidence(source_type=evidence_type, context=context)
        if evidence_item not in entry["evidence"]:
            entry["evidence"].append(evidence_item)
        entry["evidence_types"].add(evidence_type)
    
    # â”€â”€ Step 1: Collect skills from the explicit skills section â”€â”€
    # These have full categorization from the LLM
    for skill in extraction.skills_listed:
        register_skill(
            name=skill.name,
            evidence_type=EvidenceType.RESUME_SKILLS_SECTION,
            context="Listed in resume skills section",
            category=skill.category,
            parent_domain=skill.parent_domain,
        )
    
    # â”€â”€ Step 2: Collect skills from work experience descriptions â”€â”€
    for exp in extraction.work_experience:
        for skill_name in exp.skills_used:
            register_skill(
                name=skill_name,
                evidence_type=EvidenceType.RESUME_EXPERIENCE,
                context=f"Used at {exp.company} as {exp.title}",
            )
    
    # â”€â”€ Step 3: Collect skills from project descriptions â”€â”€
    for project in extraction.projects:
        for skill_name in project.technologies_used:
            register_skill(
                name=skill_name,
                evidence_type=EvidenceType.RESUME_PROJECT,
                context=f"Used in project: {project.name}",
            )
    
    # â”€â”€ Step 4: Collect skills from certifications â”€â”€
    for cert in extraction.certifications:
        for skill_name in cert.relevant_skills:
            register_skill(
                name=skill_name,
                evidence_type=EvidenceType.CERTIFICATION,
                context=f"Validated by certification: {cert.name} ({cert.issuer})",
            )
    
    # â”€â”€ Step 5: Collect skills from external sources â”€â”€
    for skill_name in extraction.github_skills:
        register_skill(
            name=skill_name,
            evidence_type=EvidenceType.GITHUB,
            context="Found on GitHub profile/repositories",
        )
    
    for skill_name in extraction.portfolio_skills:
        register_skill(
            name=skill_name,
            evidence_type=EvidenceType.PORTFOLIO,
            context="Found on portfolio website",
        )
    
    for skill_name in extraction.linkedin_skills:
        register_skill(
            name=skill_name,
            evidence_type=EvidenceType.LINKEDIN,
            context="Found on LinkedIn profile",
        )
    
    # â”€â”€ Step 6: Compute proof scores and build ScoredSkill objects â”€â”€
    scored_skills = []
    for normalized_name, data in skill_registry.items():
        score = compute_proof_score(data["evidence_types"])
        
        scored_skills.append(ScoredSkill(
            name=data["display_name"],
            category=data["category"],
            parent_domain=data["parent_domain"],
            proof_score=round(score, 2),
            evidence=data["evidence"],
            confidence_label=get_confidence_label(score),
        ))
    
    # Sort by proof score (highest first) â€” strongest skills at the top
    scored_skills.sort(key=lambda s: s.proof_score, reverse=True)
    
    return scored_skills
