"""
Interview Agent â€” The second agent in SAMAS's pipeline.

Takes the UserProfile from Agent 1 and runs a skill verification interview.
This is where candidates can prove skills their resume didn't document well,
and where we catch bluffers who listed skills they don't actually have.

GRAPH STRUCTURE:
    START â†’ select_skills â†’ generate_questions â†’ ask_question â†â”€â”
                                                    â”‚           â”‚
                                                    â–¼ (loop)    â”‚
                                              (more questions?)â”€â”˜
                                                    â”‚
                                                    â–¼ (done)
                                            evaluate_answers â†’ update_scores â†’ END

LLM CALLS: Only 2 total
    1. generate_questions â€” creates 7 questions based on skill profile
    2. evaluate_answers â€” evaluates all answers at once

HITL (Human-in-the-Loop):
    The ask_question node uses LangGraph's interrupt() to pause the graph
    and wait for human input. This is the production pattern for agents
    that need to interact with users mid-workflow.
    
    How it works:
    1. ask_question calls interrupt(question_data)
    2. Graph PAUSES â€” execution returns to the caller (main.py)
    3. Caller reads the question from graph.get_state()
    4. Caller displays question, gets user's answer
    5. Caller calls graph.ainvoke(Command(resume=answer))
    6. Graph RESUMES inside ask_question, with answer as the return value
    7. Conditional edge checks: more questions? â†’ loop or proceed
"""

import json
import random
from typing import TypedDict, List

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.llm import call_llm_with_fallback


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# INTERVIEW STATE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class InterviewState(TypedDict, total=False):
    """Shared state for the Interview Agent graph.
    
    Stages:
        0 (Input):     user_profile, num_questions
        1 (Select):    skills_to_test, high_skills, low_skills
        2 (Generate):  questions
        3 (Ask/Loop):  current_question_index, answers
        4 (Evaluate):  evaluations
        5 (Update):    updated_user_profile, interview_summary
        Throughout:    status, errors
    """
    
    # Input from Profile Builder
    user_profile: dict              # Full UserProfile dict from Agent 1
    num_questions: int              # Total questions to generate (default: 7)
    
    # Skill selection (no LLM)
    skills_to_test: list            # All selected skills
    high_skills: list               # High proof score skills (for verification MCQs)
    low_skills: list                # Low proof score skills (for assessment written Qs)
    
    # Question generation (LLM)
    questions: list                 # List of question dicts
    
    # HITL loop
    current_question_index: int     # Which question we're on (0-indexed)
    answers: list                   # Collected answers
    
    # Evaluation (LLM)
    evaluations: list               # LLM's evaluation of each answer
    
    # Output
    updated_user_profile: dict      # UserProfile with adjusted proof scores
    interview_summary: dict         # Summary of changes
    
    # Status tracking
    status: str
    errors: list


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SCORE ADJUSTMENT FORMULAS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# These are separate from the LLM â€” deterministic Python math.
# The LLM rates answer quality (0.0-1.0), these formulas
# decide how much to adjust the proof score.

def compute_verification_adjustment(answer_quality: float) -> float:
    """Score adjustment for VERIFICATION questions (testing high-score skills).
    
    The goal: catch people who listed skills they don't actually know.
    
    If they answer well   â†’ no change (score was already high, confirmed)
    If they answer poorly â†’ penalty (claimed a skill they can't demonstrate)
    
    Penalties are moderate because one question can't definitively
    prove someone doesn't know a skill â€” maybe they had a brain freeze.
    """
    if answer_quality >= 0.7:
        return 0.0     # Confirmed knowledge â€” no change needed
    elif answer_quality >= 0.4:
        return -0.05   # Slight doubt â€” small penalty
    else:
        return -0.15   # Failed verification â€” meaningful but not devastating


def compute_assessment_adjustment(answer_quality: float) -> float:
    """Score adjustment for ASSESSMENT questions (testing low-score skills).
    
    The goal: discover skills the resume didn't document well.
    
    If they answer well   â†’ boost (proved knowledge beyond the resume)
    If they answer poorly â†’ no change (score was already low, confirmed)
    
    Boosts are generous because we want to reward candidates who know
    more than their resume shows.
    """
    if answer_quality >= 0.7:
        return +0.15   # Demonstrated knowledge â€” meaningful boost
    elif answer_quality >= 0.4:
        return +0.08   # Partial knowledge â€” moderate boost
    else:
        return 0.0     # No change â€” score stays low (confirmed)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 1: SKILL SELECTION (No LLM)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•




# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 2: QUESTION GENERATION (LLM â€” 1 call)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _build_question_generation_prompt(all_skills: list) -> str:
    """Build the prompt for generating interview questions.
    
    The prompt delegates skill selection to the LLM to prioritize industry-core
    skills over niche APIs, and specifies exact MCQ vs Written distribution.
    """
    
    # Format skills with their current scores for context
    skills_str = "\n".join(
        f"  - {s['name']} (score: {s.get('proof_score', 0):.2f}, domain: {s.get('parent_domain', 'N/A')})"
        for s in all_skills
    )
    
    prompt = f"""You are an expert technical interviewer. You must design exactly 7 interview questions based on the candidate's skills.

ALL EXTRACTED SKILLS:
{skills_str if skills_str else "  (none)"}

STEP 1: SELECT SKILLS INTELLIGENTLY
From the list above, you must select exactly 14 skills to evaluate.
- Prioritize CORE industry skills (e.g., Programming Languages, Frameworks, System Design, Databases).
- AVOID niche APIs or generic tools (like Heygen, Claude API, Postman) unless there are no other options.
- Group the selected skills based on their proof scores:
  - Select exactly 4 HIGH proof score skills (score >= 0.50).
  - Select exactly 10 LOW proof score skills (score < 0.50).
(If the candidate does not have enough high or low score skills, use whatever is available to reach 14 skills total).

STEP 2: GENERATE QUESTIONS
Generate exactly 7 questions evaluating the 14 skills you selected (2 skills per question).

QUESTION FORMATTING RULES:

1. HIGH SCORE VERIFICATION (2 Questions, MCQ format):
   - Target the 4 high proof score skills (2 skills grouped per question).
   - Test if the candidate ACTUALLY knows what they claim.
   - Provide exactly 4 options (A, B, C, D) â€” only one correct.
   - Set difficulty to "verification" and question_type to "mcq".

2. LOW SCORE ASSESSMENT - MCQ (3 Questions, MCQ format):
   - Target 6 of the low proof score skills (2 skills grouped per question).
   - Give candidates a chance to PROVE hidden knowledge practically.
   - Provide exactly 4 options (A, B, C, D) â€” only one correct.
   - Set difficulty to "assessment" and question_type to "mcq".

3. LOW SCORE ASSESSMENT - WRITTEN (2 Questions, Written format):
   - Target the remaining 4 low proof score skills (2 skills grouped per question).
   - Should be answerable in 2-4 sentences.
   - Set difficulty to "assessment" and question_type to "written".

CROSS-SKILL TESTING: Each question MUST group 2 related skills naturally (e.g., FastAPI + Pydantic, or React + Typescript).
PRACTICAL: Ask about real-world usage, debugging scenarios, or design decisions. NOT trivia.

Your response must be ONLY valid JSON â€” no explanations, no markdown.

Output format:
[
  {{
    "question_id": 1,
    "question_text": "...",
    "question_type": "mcq",
    "difficulty": "verification",
    "target_skills": ["Skill1", "Skill2"],
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_option_index": 0
  }},
  {{
    "question_id": 2,
    "question_text": "...",
    "question_type": "written",
    "difficulty": "assessment",
    "target_skills": ["Skill3", "Skill4"],
    "options": null,
    "correct_option_index": null
  }}
]"""
    
    return prompt


from langchain_core.runnables import RunnableConfig

async def generate_questions_node(state: InterviewState, config: RunnableConfig) -> dict:
    """Generate interview questions using the LLM.
    
    This is LLM call #1 of 2 in the interview pipeline.
    It receives the selected skills and produces structured questions.
    """
    profile = state.get("user_profile", {})
    all_skills = profile.get("skills", [])
    existing_errors = state.get("errors", [])
    
    if not all_skills:
        return {
            "questions": [],
            "current_question_index": 0,
            "answers": [],
            "status": "no_skills_to_test",
            "errors": existing_errors + ["No skills found in profile for testing"],
        }
    
    print(f"Generating 7 interview questions intelligently from {len(all_skills)} total skills...")
    
    prompt = _build_question_generation_prompt(all_skills)
    
    messages = [
        SystemMessage(content=(
            "You are a technical interviewer. Generate interview questions "
            "in valid JSON format only. No explanations."
        )),
        HumanMessage(content=prompt),
    ]
    
    # Extract BYOK Config
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    custom_model = configurable.get("custom_model")
    
    try:
        result = await call_llm_with_fallback(
            messages, 
            label="Question Gen",
            custom_api_key=custom_api_key,
            custom_model=custom_model
        )
        questions = result["data"]
        
        # Ensure it's a list
        if isinstance(questions, dict):
            questions = questions.get("questions", [questions])
        
        print(f"   Generated {len(questions)} questions")
        
        # Log question types
        mcq_count = sum(1 for q in questions if q.get("question_type") == "mcq")
        written_count = len(questions) - mcq_count
        print(f"   {mcq_count} MCQ (verification) + {written_count} written (assessment)")
        
        return {
            "questions": questions,
            "current_question_index": 0,
            "answers": [],
            "status": "questions_generated",
            "errors": existing_errors,
        }
        
    except Exception as e:
        error_msg = f"Question generation failed: {str(e)}"
        print(f"   {error_msg}")
        return {
            "questions": [],
            "current_question_index": 0,
            "answers": [],
            "status": "question_generation_failed",
            "errors": existing_errors + [error_msg],
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 3: ASK QUESTIONS (HITL â€” No LLM)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def ask_questions_node(state: InterviewState) -> dict:
    """Present all questions to the user at once and wait for their answers.
    
    This is refactored for Web UI compatibility. A stateless web app needs
    to fetch all questions, show them to the user (even if one-by-one on the client),
    and then submit all answers in one go.
    """
    questions = state.get("questions", [])
    if not questions:
        return state
        
    # Build the interrupt payload â€” containing all questions
    interrupt_payload = {
        "type": "interview_questions",
        "questions": [
            {
                "question_id": q.get("question_id"),
                "question_number": i + 1,
                "question_type": q.get("question_type", "written"),
                "difficulty": q.get("difficulty", "assessment"),
                "target_skills": q.get("target_skills", []),
                "question_text": q.get("question_text", ""),
                "options": q.get("options"),
            }
            for i, q in enumerate(questions)
        ]
    }
    
    # â”€â”€â”€â”€ INTERRUPT: GRAPH PAUSES HERE â”€â”€â”€â”€
    user_answers = interrupt(interrupt_payload)
    # â”€â”€â”€â”€ GRAPH RESUMES HERE WITH ANSWERS â”€â”€
    
    # Process the returned array of answers
    # Expected format: [{"question_id": 1, "answer": "User text"}, ...]
    
    formatted_answers = []
    
    # Handle dict (single answer, shouldn't happen but safe to handle) or list (expected)
    if isinstance(user_answers, dict):
        user_answers = [user_answers]
        
    for ans in user_answers:
        q_id = ans.get("question_id")
        q_text = ans.get("answer", "")
        
        # Find matching question context
        matching_q = next((q for q in questions if q.get("question_id") == q_id), None)
        if matching_q:
            formatted_answers.append({
                "question_id": q_id,
                "user_answer": q_text,
                "target_skills": matching_q.get("target_skills", []),
                "question_type": matching_q.get("question_type", "written"),
                "difficulty": matching_q.get("difficulty", "assessment"),
            })
    
    return {
        "answers": formatted_answers,
        "current_question_index": len(questions),
        "status": "answers_received"
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 4: EVALUATE ANSWERS (LLM â€” 1 call)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _build_evaluation_prompt(questions: list, answers: list) -> str:
    """Build the prompt for evaluating interview answers."""
    
    qa_pairs = []
    for answer in answers:
        qid = answer["question_id"]
        # Find the matching question
        question = next(
            (q for q in questions if q.get("question_id") == qid),
            None
        )
        if question:
            pair = {
                "question_id": qid,
                "question_text": question.get("question_text", ""),
                "question_type": question.get("question_type", "written"),
                "difficulty": question.get("difficulty", "assessment"),
                "target_skills": question.get("target_skills", []),
                "user_answer": answer["user_answer"],
            }
            if question.get("options"):
                pair["options"] = question["options"]
                pair["correct_option_index"] = question.get("correct_option_index")
            qa_pairs.append(pair)
    
    prompt = f"""You are evaluating a candidate's interview answers. Assess each answer fairly.

QUESTIONS AND ANSWERS:
{json.dumps(qa_pairs, indent=2)}

EVALUATION RULES:
1. For MCQ (verification) questions:
   - If the correct option was selected â†’ answer_quality = 1.0
   - If wrong option selected â†’ answer_quality = 0.0 to 0.2 (based on how close the reasoning was)

2. For written (assessment) questions:
   - 1.0 = Perfect â€” demonstrates clear mastery and practical understanding
   - 0.7 = Good â€” shows practical knowledge with minor gaps
   - 0.4 = Partial â€” has some understanding but significant gaps
   - 0.1 = Poor â€” mostly wrong or irrelevant
   - 0.0 = No answer or completely wrong

3. Be FAIR:
   - One question can NOT definitively prove or disprove skill mastery
   - Give partial credit for right approach even with small errors
   - Evaluate depth of understanding, not answer length
   - Consider that the candidate is under time pressure

4. For each skill tested by a question, rate how well the answer
   demonstrates knowledge of THAT SPECIFIC skill (0.0 to 1.0)

Your response must be ONLY valid JSON â€” no explanations.

Output format:
[
  {{
    "question_id": 1,
    "answer_quality": 0.8,
    "feedback": "Good understanding of X, but missed Y...",
    "skill_scores": {{
      "SkillName1": 0.9,
      "SkillName2": 0.7
    }}
  }}
]"""
    
    return prompt


async def evaluate_answers_node(state: InterviewState, config: RunnableConfig) -> dict:
    """Evaluate all interview answers using the LLM.
    
    This is LLM call #2 of 2 in the interview pipeline.
    It receives all Q&A pairs and produces evaluations.
    """
    questions = state.get("questions", [])
    answers = state.get("answers", [])
    existing_errors = state.get("errors", [])
    
    if not answers:
        return {
            "evaluations": [],
            "status": "no_answers_to_evaluate",
            "errors": existing_errors + ["No answers collected"],
        }
    
    print(f"\nEvaluating {len(answers)} answers...")
    
    prompt = _build_evaluation_prompt(questions, answers)
    
    messages = [
        SystemMessage(content=(
            "You are a fair technical interviewer evaluating answers. "
            "Respond with valid JSON only."
        )),
        HumanMessage(content=prompt),
    ]
    
    # Extract BYOK Config
    configurable = config.get("configurable", {})
    custom_api_key = configurable.get("custom_api_key")
    custom_model = configurable.get("custom_model")
    
    try:
        result = await call_llm_with_fallback(
            messages, 
            label="Evaluator",
            custom_api_key=custom_api_key,
            custom_model=custom_model
        )
        evaluations = result["data"]
        
        if isinstance(evaluations, dict):
            evaluations = evaluations.get("evaluations", [evaluations])
        
        # Log evaluation results
        for ev in evaluations:
            qid = ev.get("question_id", "?")
            quality = ev.get("answer_quality", 0)
            label = "" if quality >= 0.7 else "â–³" if quality >= 0.4 else ""
            print(f"   {label} Q{qid}: {quality:.1f} â€” {ev.get('feedback', '')[:60]}")
        
        return {
            "evaluations": evaluations,
            "status": "evaluation_complete",
            "errors": existing_errors,
        }
        
    except Exception as e:
        error_msg = f"Answer evaluation failed: {str(e)}"
        print(f"   {error_msg}")
        return {
            "evaluations": [],
            "status": "evaluation_failed",
            "errors": existing_errors + [error_msg],
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NODE 5: UPDATE SCORES (No LLM â€” Pure Python)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def update_scores_node(state: InterviewState) -> dict:
    """Apply score adjustments based on interview evaluations.
    
    The LLM rated each answer's quality. Now we use our deterministic
    formulas to adjust proof scores. The LLM evaluates, Python does math.
    
    Rules (matching user's requirements):
    - VERIFICATION (high score) + wrong answer â†’ penalty (-0.15)
    - VERIFICATION (high score) + right answer â†’ no change (confirmed)
    - ASSESSMENT (low score) + right answer â†’ boost (+0.15)
    - ASSESSMENT (low score) + wrong answer â†’ no change (stays low)
    """
    profile = state.get("user_profile", {})
    evaluations = state.get("evaluations", [])
    answers = state.get("answers", [])
    existing_errors = state.get("errors", [])
    
    if not evaluations:
        return {
            "updated_user_profile": profile,
            "interview_summary": {"error": "No evaluations available"},
            "status": "skipped_score_update",
            "errors": existing_errors,
        }
    
    print("\nComputing score adjustments...")
    
    # Build a lookup: skill_name â†’ current skill dict
    skills = list(profile.get("skills", []))
    skill_lookup = {s["name"].lower(): i for i, s in enumerate(skills)}
    
    # Build answer lookup for difficulty info
    answer_lookup = {}
    for ans in answers:
        answer_lookup[ans["question_id"]] = ans
    
    # Track all adjustments for the summary
    all_adjustments = []
    skills_modified = set()
    
    for evaluation in evaluations:
        qid = evaluation.get("question_id")
        answer_info = answer_lookup.get(qid, {})
        difficulty = answer_info.get("difficulty", "assessment")
        skill_scores = evaluation.get("skill_scores", {})
        
        for skill_name, demonstrated_knowledge in skill_scores.items():
            skill_key = skill_name.lower()
            if skill_key not in skill_lookup:
                # Skill not in profile â€” skip
                continue
            
            skill_idx = skill_lookup[skill_key]
            original_score = skills[skill_idx].get("proof_score", 0.0)
            
            # Apply the right formula based on question type
            if difficulty == "verification":
                adjustment = compute_verification_adjustment(demonstrated_knowledge)
            else:
                adjustment = compute_assessment_adjustment(demonstrated_knowledge)
            
            # If we've already adjusted this skill, take the one with larger magnitude
            # (prevents contradictory adjustments from different questions)
            if skill_key in skills_modified:
                existing = next(
                    (a for a in all_adjustments if a["skill_name"].lower() == skill_key),
                    None
                )
                if existing and abs(adjustment) <= abs(existing["adjustment"]):
                    continue  # Keep the larger adjustment
                elif existing:
                    # Replace with larger adjustment
                    all_adjustments.remove(existing)
            
            # Clamp the new score between 0.0 and 1.0
            new_score = max(0.0, min(1.0, original_score + adjustment))
            
            adjustment_record = {
                "skill_name": skills[skill_idx]["name"],
                "original_score": round(original_score, 2),
                "demonstrated_knowledge": round(demonstrated_knowledge, 2),
                "adjustment": round(adjustment, 2),
                "new_score": round(new_score, 2),
                "reason": _describe_adjustment(difficulty, demonstrated_knowledge, adjustment),
            }
            
            all_adjustments.append(adjustment_record)
            skills_modified.add(skill_key)
            
            # Apply the adjustment to the skill
            skills[skill_idx]["proof_score"] = round(new_score, 2)
            
            # Update confidence label based on new score
            skills[skill_idx]["confidence_label"] = _score_to_label(new_score)
    
    # Build the updated profile
    updated_profile = dict(profile)
    updated_profile["skills"] = skills
    
    # Build summary
    boosted = sum(1 for a in all_adjustments if a["adjustment"] > 0)
    penalized = sum(1 for a in all_adjustments if a["adjustment"] < 0)
    unchanged = sum(1 for a in all_adjustments if a["adjustment"] == 0)
    
    avg_quality = 0.0
    if evaluations:
        avg_quality = sum(e.get("answer_quality", 0) for e in evaluations) / len(evaluations)
    
    summary = {
        "total_questions": len(state.get("questions", [])),
        "questions_answered": len(answers),
        "average_answer_quality": round(avg_quality, 2),
        "skills_boosted": boosted,
        "skills_penalized": penalized,
        "skills_unchanged": unchanged,
        "adjustments": sorted(
            all_adjustments,
            key=lambda x: abs(x["adjustment"]),
            reverse=True,
        ),
    }
    
    print(f"   {boosted} skills boosted, {penalized} penalized, {unchanged} unchanged")
    
    return {
        "updated_user_profile": updated_profile,
        "interview_summary": summary,
        "status": "interview_complete",
        "errors": existing_errors,
    }


def _describe_adjustment(difficulty: str, knowledge: float, adjustment: float) -> str:
    """Generate a human-readable reason for a score change."""
    if adjustment > 0:
        return f"Demonstrated knowledge ({knowledge:.1f}) in assessment â†’ +{adjustment:.2f} boost"
    elif adjustment < 0:
        return f"Weak answer ({knowledge:.1f}) on verification â†’ {adjustment:.2f} penalty"
    elif difficulty == "verification":
        return f"Confirmed knowledge ({knowledge:.1f}) â€” score maintained"
    else:
        return f"Limited demonstration ({knowledge:.1f}) â€” score unchanged"


def _score_to_label(score: float) -> str:
    """Convert a proof score to a confidence label."""
    if score >= 0.75:
        return "Very High"
    elif score >= 0.50:
        return "High"
    elif score >= 0.30:
        return "Medium"
    else:
        return "Low"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GRAPH DEFINITION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def build_interview_graph():
    """Build and compile the Interview Agent's LangGraph.
    
    Graph structure:
        START â†’ select_skills â†’ generate_questions â†’ ask_question
              â†’ (conditional: more? â†’ ask_question, done? â†’ evaluate_answers)
              â†’ update_scores â†’ END
    
    The ask_question node uses interrupt() for HITL, creating a loop
    where each iteration pauses for user input.
    
    The MemorySaver checkpointer is ESSENTIAL here â€” it remembers the
    graph state between interrupt/resume cycles. Without it, the graph
    would forget everything each time we call ainvoke().
    """
    graph = StateGraph(InterviewState)
    
    # Register nodes
    graph.add_node("generate_questions", generate_questions_node)
    graph.add_node("ask_questions", ask_questions_node)
    graph.add_node("evaluate_answers", evaluate_answers_node)
    graph.add_node("update_scores", update_scores_node)
    
    # Linear edges for stateless Web UI flow
    # generate -> ask (interrupt) -> evaluate -> update -> end
    graph.add_edge(START, "generate_questions")
    graph.add_edge("generate_questions", "ask_questions")
    graph.add_edge("ask_questions", "evaluate_answers")
    graph.add_edge("evaluate_answers", "update_scores")
    graph.add_edge("update_scores", END)
    
    # MemorySaver is critical for HITL â€” it preserves state across
    # interrupt/resume cycles. Without this, the graph would "forget"
    # everything when we resume after each question.
    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)
    
    return compiled
