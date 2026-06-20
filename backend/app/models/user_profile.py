"""
User Profile Schema â€” The heart of SAMAS's data model.

This module defines TWO layers of schemas:

Layer 1: ResumeExtraction (what the LLM outputs)
    - The LLM reads resume text + scraped data
    - It extracts information into this schema
    - NO proof scores here â€” LLMs are bad at math
    - The LLM's job is just: "tell me what you see"

Layer 2: UserProfile (what our Python code produces)
    - Takes the raw extraction from Layer 1
    - Computes proof scores using our evidence-tiering formula
    - This is the final output that goes to job matching

WHY two layers?
    - Separation of concerns: LLM extracts, code scores
    - Easier to debug: if scores are wrong, it's our formula, not the LLM
    - More reliable: LLMs hallucinate math, our formula is deterministic

SKILL EXTRACTION PHILOSOPHY:
    We don't extract broad languages ("Python", "JavaScript").
    We extract GRANULAR skills: frameworks, libraries, concepts, approaches.
    "Python" becomes: "FastAPI", "Pandas", "asyncio", "Pydantic"
    "ML" becomes: "Transformers", "Attention Mechanism", "Linear Algebra", "CNNs"
    
    Why? Because job descriptions ask for "FastAPI experience", not "Python".
    Granular skills = better job matching = less rejection.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, model_validator


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENUMS â€” Categorization constants used across the schema
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class SkillCategory(str, Enum):
    """How we classify each granular skill.
    
    These categories help us group skills in the UI and match them
    against JD requirements. A job asking for "frameworks" maps to
    FRAMEWORK; one asking for "cloud experience" maps to PLATFORM.
    """
    FRAMEWORK = "framework"           # React, FastAPI, Spring Boot, LangChain
    LIBRARY = "library"               # Pandas, NumPy, Lodash, Scikit-learn
    TOOL = "tool"                     # Docker, Git, Webpack, Postman
    PLATFORM = "platform"             # AWS, GCP, Azure, Vercel
    DATABASE = "database"             # PostgreSQL, MongoDB, Redis, DynamoDB
    CONCEPT = "concept"               # Microservices, REST API, GraphQL, OAuth
    ALGORITHM = "algorithm"           # DFS, BFS, Dynamic Programming, A*
    DATA_STRUCTURE = "data_structure"  # Binary Trees, Hash Maps, Graphs, Tries
    MATH = "math"                     # Linear Algebra, Probability, Calculus
    METHODOLOGY = "methodology"       # Agile, Scrum, TDD, CI/CD
    DOMAIN = "domain"                 # NLP, Computer Vision, System Design
    LANGUAGE_FEATURE = "language_feature"  # async/await, decorators, generics
    DESIGN_PATTERN = "design_pattern"     # Observer, Factory, Singleton
    OTHER = "other"                   # Anything that doesn't fit above


class EvidenceType(str, Enum):
    """Where a skill was found â€” each source type has a different
    weight in our proof score formula.
    
    The key insight: everything in the resume is ONE source (self-reported).
    GitHub, portfolio, LinkedIn are INDEPENDENT corroboration.
    """
    # Resume sources (self-reported â€” we take the max, not sum)
    RESUME_SKILLS_SECTION = "resume_skills_section"
    RESUME_PROJECT = "resume_project"
    RESUME_EXPERIENCE = "resume_experience"
    
    # External sources (independent â€” these stack additively)
    GITHUB = "github"
    PORTFOLIO = "portfolio"
    LINKEDIN = "linkedin"
    CERTIFICATION = "certification"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 1: LLM EXTRACTION SCHEMAS
# These are what the LLM fills. Simple, no scoring logic.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ExtractedPersonalInfo(BaseModel):
    """Basic identity info. No proof scoring needed here â€”
    we just believe what the resume says about name/email/etc."""
    
    full_name: str = Field(
        description="Candidate's full name as written on the resume"
    )
    email: Optional[str] = Field(
        None, description="Email address"
    )
    phone: Optional[str] = Field(
        None, description="Phone number including country code if present"
    )
    city: Optional[str] = Field(
        None, description="City of residence"
    )
    state: Optional[str] = Field(
        None, description="State or province"
    )
    country: Optional[str] = Field(
        None, description="Country of residence"
    )
    linkedin_url: Optional[str] = Field(
        None, description="LinkedIn profile URL"
    )
    github_url: Optional[str] = Field(
        None, description="GitHub profile URL"
    )
    portfolio_url: Optional[str] = Field(
        None, description="Personal portfolio or website URL"
    )
    other_urls: List[str] = Field(
        default_factory=list,
        description="Any other relevant URLs (blog, Behance, Dribbble, etc.)"
    )
    professional_summary: Optional[str] = Field(
        None,
        description="Summary/objective statement from top of resume"
    )


class ExtractedEducation(BaseModel):
    """A single education entry. No proof scoring â€” we trust
    education claims (verifying university attendance is out of scope)."""
    
    institution: str = Field(
        description="Name of the university, college, or school"
    )
    degree: str = Field(
        description="Degree type: B.Tech, B.Sc, M.S., MBA, Ph.D., etc."
    )
    field_of_study: str = Field(
        description="Major or specialization: Computer Science, Electronics, etc."
    )
    start_date: Optional[str] = Field(
        None, description="Start date in any format the resume uses"
    )
    end_date: Optional[str] = Field(
        None, description="End date, graduation year, or 'Present'"
    )
    is_current: bool = Field(
        False, description="True if currently studying here"
    )
    gpa: Optional[str] = Field(
        None,
        description="GPA, CGPA, or percentage as written (e.g. '8.5/10', '3.7/4.0', '85%')"
    )
    relevant_coursework: List[str] = Field(
        default_factory=list,
        description="Courses listed as relevant (e.g. 'Data Structures', 'Machine Learning')"
    )
    achievements: List[str] = Field(
        default_factory=list,
        description="Academic honors, dean's list, scholarships, etc."
    )


class ExtractedSkillEntry(BaseModel):
    """A single granular skill with its classification.
    
    This is used in the skills_listed field â€” the LLM categorizes each
    skill it finds in the resume's skills/technical skills section.
    
    IMPORTANT: Skills must be SPECIFIC, not vague.
    âœ… "FastAPI", "React Query", "Binary Trees", "Attention Mechanism"
    âŒ "Python", "JavaScript", "Web Development" (too broad)
    """
    
    name: str = Field(
        description="Specific skill name. Must be granular: 'FastAPI' not 'Python'",
        min_length=1,
        max_length=100
    )
    category: SkillCategory = Field(
        description="What type of skill this is (framework, concept, tool, etc.)"
    )
    parent_domain: str = Field(
        description="Broader domain this belongs to: 'Python', 'Deep Learning', 'DSA', 'DevOps'",
        min_length=1,
        max_length=100
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_category(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cat = data.get("category")
            if isinstance(cat, str):
                try:
                    SkillCategory(cat)
                except ValueError:
                    data["category"] = "other"
        return data


class ExtractedWorkExperience(BaseModel):
    """A single work experience entry.
    
    We don't proof-score the experience itself (we believe they worked there).
    But we DO extract skills_used â€” these feed into our skill proof scoring.
    If someone says they used FastAPI at Company X, that's evidence for FastAPI.
    """
    
    company: str = Field(description="Company or organization name")
    title: str = Field(description="Job title / designation")
    location: Optional[str] = Field(
        None, description="Work location or 'Remote'"
    )
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date or 'Present'")
    is_current: bool = Field(False, description="Currently working here")
    description: str = Field(
        description="Full description of the role and responsibilities"
    )
    responsibilities: List[str] = Field(
        default_factory=list,
        description="Key responsibilities as bullet points"
    )
    skills_used: List[str] = Field(
        default_factory=list,
        description=(
            "Technical skills, frameworks, tools mentioned in this role's description. "
            "Be granular: 'FastAPI' not 'Python', 'React Query' not 'JavaScript'"
        )
    )


class ExtractedProject(BaseModel):
    """A project from the resume â€” personal, academic, or professional.
    
    technologies_used feeds directly into skill proof scoring.
    If someone built a project WITH a technology, that's stronger evidence
    than just listing it in the skills section.
    """
    
    name: str = Field(description="Project name or title")
    description: str = Field(description="What the project does and its purpose")
    url: Optional[str] = Field(None, description="Live demo or deployment URL")
    github_url: Optional[str] = Field(None, description="Source code repository URL")
    technologies_used: List[str] = Field(
        default_factory=list,
        description=(
            "Specific technologies used in this project. "
            "Be granular: 'Next.js' not 'JavaScript', 'LangGraph' not 'AI'"
        )
    )
    role: Optional[str] = Field(
        None, description="Your role if this was a team project"
    )
    key_achievements: List[str] = Field(
        default_factory=list,
        description="Notable outcomes, metrics, or achievements from this project"
    )


class ExtractedCertification(BaseModel):
    """A certification, course completion, or professional credential.
    
    relevant_skills connects this cert to specific skills for proof scoring.
    Having a 'Kubernetes Administrator' cert is evidence for the 'Kubernetes' skill.
    """
    
    name: str = Field(description="Certification or course name")
    issuer: str = Field(description="Issuing organization (AWS, Google, Coursera, etc.)")
    date: Optional[str] = Field(None, description="Date obtained or completion date")
    url: Optional[str] = Field(None, description="Verification or credential URL")
    credential_id: Optional[str] = Field(None, description="Credential ID if provided")
    relevant_skills: List[str] = Field(
        default_factory=list,
        description="Specific skills this certification validates"
    )


class ExtractedPublication(BaseModel):
    """A research paper, blog post, article, or conference talk."""
    
    title: str = Field(description="Publication title")
    publisher: Optional[str] = Field(
        None, description="Journal, conference, blog platform, etc."
    )
    date: Optional[str] = Field(None, description="Publication date")
    url: Optional[str] = Field(None, description="Link to the publication")
    description: Optional[str] = Field(None, description="Brief summary")


class ExtractedAchievement(BaseModel):
    """An award, competition result, hackathon win, or notable achievement."""
    
    title: str = Field(description="Achievement title or name")
    issuer: Optional[str] = Field(
        None, description="Organization that gave the award"
    )
    date: Optional[str] = Field(None, description="When it was received")
    description: Optional[str] = Field(None, description="Details about the achievement")

    @model_validator(mode="before")
    @classmethod
    def coerce_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"title": data}
        return data


class ExtractedVolunteer(BaseModel):
    """Volunteer work, club leadership, community involvement."""
    
    organization: str = Field(description="Organization or community name")
    role: str = Field(description="Your role or title")
    description: Optional[str] = Field(None, description="What you did")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")


class ExtractedLanguage(BaseModel):
    """A spoken/written language (NOT programming languages).
    Hindi, English, Tamil, etc."""
    
    language: str = Field(description="Language name")
    proficiency: Optional[str] = Field(
        None,
        description="Proficiency: basic, conversational, professional, native/fluent"
    )


# â”€â”€â”€ The Main Extraction Schema (Layer 1 output) â”€â”€â”€â”€â”€

class ResumeExtraction(BaseModel):
    """Complete structured extraction from resume + external sources.
    
    This is what the LLM fills. Note what's NOT here: proof scores.
    The LLM's only job is extraction â€” identifying what's in the data.
    
    After this is filled, our Python code in scoring.py takes over
    to compute proof scores by cross-referencing evidence sources.
    """
    
    personal_info: ExtractedPersonalInfo = Field(
        description="Basic identifying information"
    )
    education: List[ExtractedEducation] = Field(
        default_factory=list,
        description="All education entries, most recent first"
    )
    work_experience: List[ExtractedWorkExperience] = Field(
        default_factory=list,
        description="All work experience entries, most recent first"
    )
    projects: List[ExtractedProject] = Field(
        default_factory=list,
        description="Personal, academic, and professional projects"
    )
    skills_listed: List[ExtractedSkillEntry] = Field(
        default_factory=list,
        description=(
            "Skills from the resume's explicit skills/technical skills section. "
            "Extract GRANULAR skills: specific frameworks, libraries, concepts. "
            "NOT broad languages like 'Python' or 'JavaScript'."
        )
    )
    certifications: List[ExtractedCertification] = Field(
        default_factory=list,
        description="Professional certifications and completed courses"
    )
    publications: List[ExtractedPublication] = Field(
        default_factory=list,
        description="Research papers, blog posts, articles, talks"
    )
    achievements: List[ExtractedAchievement] = Field(
        default_factory=list,
        description="Awards, competition results, hackathon wins"
    )
    volunteer_experience: List[ExtractedVolunteer] = Field(
        default_factory=list,
        description="Volunteer work, club activities, community involvement"
    )
    spoken_languages: List[ExtractedLanguage] = Field(
        default_factory=list,
        description="Human languages (English, Hindi, etc.), NOT programming"
    )
    interests: List[str] = Field(
        default_factory=list,
        description="Hobbies and interests if mentioned"
    )
    
    # â”€â”€â”€ External source data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # These fields are filled when we have scraped data from
    # GitHub, portfolio, LinkedIn, etc. The LLM identifies
    # skills visible on these platforms.
    
    github_skills: List[str] = Field(
        default_factory=list,
        description=(
            "Skills identified from GitHub: repo languages, frameworks in READMEs, "
            "tools in config files. Be granular."
        )
    )
    portfolio_skills: List[str] = Field(
        default_factory=list,
        description="Skills identified from portfolio website projects and descriptions"
    )
    linkedin_skills: List[str] = Field(
        default_factory=list,
        description="Skills visible on LinkedIn profile (endorsements, listed skills)"
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 2: FINAL OUTPUT SCHEMAS
# These have proof scores computed by Python code.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class SkillEvidence(BaseModel):
    """A single piece of evidence for a skill.
    
    We track every place we found evidence of this skill so we can:
    1. Show the user WHY we scored their skill this way
    2. Debug scoring issues
    3. Present transparent, trustworthy assessments
    """
    
    source_type: EvidenceType = Field(
        description="The type of source where this skill was found"
    )
    context: str = Field(
        description="Specific context: 'Used in E-commerce Dashboard project' or 'Found in GitHub repo: my-api'",
        min_length=1
    )


class ScoredSkill(BaseModel):
    """A skill with proof scoring â€” the core of SAMAS's differentiation.
    
    This is what makes us different from every other job tool:
    we don't just list skills, we score them based on EVIDENCE.
    
    A skill with score 0.25 = "just claimed in skills section"
    A skill with score 0.75 = "used in projects + found on GitHub"
    
    This honesty helps users understand where they truly stand
    and reduces wasted applications on jobs they can't get.
    """
    
    name: str = Field(description="The granular skill name")
    category: SkillCategory = Field(description="Skill classification")
    parent_domain: str = Field(description="Broader domain this belongs to")
    proof_score: float = Field(
        ge=0.0, le=1.0,
        description="Evidence-based score from 0.0 (no proof) to 1.0 (strong proof)"
    )
    evidence: List[SkillEvidence] = Field(
        description="All sources where this skill was found"
    )
    confidence_label: str = Field(
        description="Human-readable label: 'Low', 'Medium', 'High', or 'Very High'"
    )


class ExtractionMetadata(BaseModel):
    """Metadata about how this profile was built.
    
    Useful for debugging, auditing, and showing users
    the transparency of our process.
    """
    
    resume_filename: str = Field(description="Original resume file name")
    external_urls_scraped: List[str] = Field(
        default_factory=list,
        description="URLs we successfully scraped for additional data"
    )
    extraction_timestamp: str = Field(
        description="When this profile was built (ISO format)"
    )
    llm_model_used: str = Field(
        description="Which LLM model performed the extraction"
    )
    total_skills_extracted: int = Field(
        description="Total number of unique skills found"
    )
    average_proof_score: float = Field(
        description="Average proof score across all skills"
    )
    score_distribution: dict = Field(
        default_factory=dict,
        description="How many skills fall into each confidence tier"
    )


class UserProfile(BaseModel):
    """The complete, final user profile â€” output of the Profile Builder agent.
    
    This is the single source of truth about a candidate. Everything
    downstream (job matching, interview prep, resume tailoring) reads
    from this schema.
    
    Key design decisions:
    - Skills are the ONLY thing with proof scores (not education, not experience)
    - Skills are granular (frameworks, not languages)
    - Evidence is tracked and displayed for transparency
    - Metadata tracks how the profile was built
    """
    
    personal_info: ExtractedPersonalInfo
    education: List[ExtractedEducation]
    work_experience: List[ExtractedWorkExperience]
    projects: List[ExtractedProject]
    
    # THE CORE â€” proof-scored, granular skills
    skills: List[ScoredSkill] = Field(
        description="All skills with proof scores, sorted by score descending"
    )
    
    certifications: List[ExtractedCertification]
    publications: List[ExtractedPublication]
    achievements: List[ExtractedAchievement]
    volunteer_experience: List[ExtractedVolunteer]
    spoken_languages: List[ExtractedLanguage]
    interests: List[str]
    
    extraction_metadata: ExtractionMetadata
