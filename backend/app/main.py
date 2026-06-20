"""
SAMAS â€” Multi-Agent Pipeline Runner.

This CLI runs the full SAMAS pipeline:
    Phase 1: Profile Builder Agent â†’ extracts resume + computes proof scores
    Phase 2: Interview Agent â†’ verifies skills via HITL interview â†’ adjusts scores

The two agents are separate LangGraph instances that run sequentially.
Agent 1's output (UserProfile) feeds into Agent 2's input.

Run with: python -m app.main
"""

import asyncio
import json
import uuid
import sys
from pathlib import Path

# Fix Windows cp1252 encoding issues when printing emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command

from app.agents.profile_builder import build_profile_builder_graph
from app.agents.interview_agent import build_interview_graph
from app.agents.job_search_agent import build_job_search_graph
from app.agents.jd_analyzer_agent import build_jd_analyzer_graph
from app.agents.matching_agent import build_matching_graph
from app.models.job import JobListing


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DISPLAY HELPERS â€” Pretty terminal output
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def display_profile_summary(profile: dict):
    """Show a summary of the extracted profile with skill scores."""
    personal = profile.get("personal_info", {})
    skills = profile.get("skills", [])
    metadata = profile.get("extraction_metadata", {})
    
    print(f"\nðŸ‘¤ Name: {personal.get('full_name', 'Unknown')}")
    print(f"ðŸ“§ Email: {personal.get('email', 'N/A')}")
    print(f"ðŸ“ Location: {personal.get('city', 'N/A')}, {personal.get('country', 'N/A')}")
    print(f"ðŸ”— GitHub: {personal.get('github_url', 'N/A')}")
    print(f"ðŸ”— LinkedIn: {personal.get('linkedin_url', 'N/A')}")
    
    print(f"\nðŸ“Š Skills Extracted: {len(skills)}")
    print(f"ðŸ“Š Average Proof Score: {metadata.get('average_proof_score', 0):.2f}")
    print(f"ðŸ“Š Distribution: {metadata.get('score_distribution', {})}")
    
    if skills:
        print(f"\n{'â”€' * 60}")
        print(f"  TOP SKILLS (sorted by proof score)")
        print(f"{'â”€' * 60}")
        print(f"  {'Skill':<30} {'Score':<8} {'Confidence':<12} {'Domain'}")
        print(f"  {'â”€'*30} {'â”€'*8} {'â”€'*12} {'â”€'*15}")
        
        for skill in skills[:20]:
            name = skill.get("name", "?")
            score = skill.get("proof_score", 0)
            confidence = skill.get("confidence_label", "?")
            domain = skill.get("parent_domain", "?")
            print(f"  {name:<30} {score:<8.2f} {confidence:<12} {domain}")
        
        if len(skills) > 20:
            print(f"  ... and {len(skills) - 20} more skills")


def display_interview_question(question_data: dict):
    """Format and display one interview question from the HITL interrupt."""
    q_num = question_data.get("question_number", "?")
    total = question_data.get("total_questions", "?")
    q_type = question_data.get("question_type", "written")
    difficulty = question_data.get("difficulty", "assessment")
    skills = question_data.get("target_skills", [])
    text = question_data.get("question_text", "")
    options = question_data.get("options")
    
    # Type label
    type_label = "MCQ â€” Verification" if q_type == "mcq" else "Written â€” Assessment"
    
    print(f"\n{'â”€' * 60}")
    print(f"  ðŸ“ Question {q_num} of {total}  ({type_label})")
    print(f"  Testing: {', '.join(skills)}")
    print(f"{'â”€' * 60}")
    print(f"\n  {text}\n")
    
    if options:
        for option in options:
            print(f"    {option}")
        print()


def display_interview_results(summary: dict, profile: dict):
    """Show the interview results with score changes."""
    print(f"\n{'â•' * 60}")
    print(f"  INTERVIEW RESULTS")
    print(f"{'â•' * 60}")
    
    print(f"\n  Questions answered: {summary.get('questions_answered', 0)}/{summary.get('total_questions', 0)}")
    print(f"  Average answer quality: {summary.get('average_answer_quality', 0):.2f}")
    print(f"\n  Skills boosted:    {summary.get('skills_boosted', 0)} â†‘")
    print(f"  Skills penalized:  {summary.get('skills_penalized', 0)} â†“")
    print(f"  Skills unchanged:  {summary.get('skills_unchanged', 0)} â†’")
    
    adjustments = summary.get("adjustments", [])
    if adjustments:
        print(f"\n{'â”€' * 60}")
        print(f"  SCORE CHANGES")
        print(f"{'â”€' * 60}")
        print(f"  {'Skill':<25} {'Before':<8} {'After':<8} {'Change':<10} {'Reason'}")
        print(f"  {'â”€'*25} {'â”€'*8} {'â”€'*8} {'â”€'*10} {'â”€'*30}")
        
        for adj in adjustments:
            name = adj.get("skill_name", "?")[:24]
            before = adj.get("original_score", 0)
            after = adj.get("new_score", 0)
            change = adj.get("adjustment", 0)
            reason = adj.get("reason", "")[:40]
            
            # Color indicator
            if change > 0:
                indicator = f"+{change:.2f} â†‘"
            elif change < 0:
                indicator = f"{change:.2f} â†“"
            else:
                indicator = " 0.00 â†’"
            
            print(f"  {name:<25} {before:<8.2f} {after:<8.2f} {indicator:<10} {reason}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 1: PROFILE BUILDER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def run_profile_builder() -> dict | None:
    """Run the Profile Builder agent. Returns the UserProfile dict or None."""
    
    print("=" * 60)
    print("  SAMAS â€” Phase 1: Profile Builder")
    print("=" * 60)
    print()
    
    # Get resume path
    resume_path = input("ðŸ“„ Enter path to your resume (PDF or DOCX): ").strip()
    if not resume_path:
        print("No resume path provided. Exiting.")
        return None
    
    resume_path = resume_path.strip('"').strip("'")
    if not Path(resume_path).exists():
        print(f"âŒ File not found: {resume_path}")
        return None
    
    # Get external URLs
    print()
    print("ðŸ”— Enter external URLs (one per line). Press Enter on empty line when done:")
    print("   Examples: https://github.com/yourname, https://linkedin.com/in/yourname")
    
    external_urls = []
    while True:
        url = input("   URL: ").strip()
        if not url:
            break
        for u in url.split(','):
            u = u.strip()
            if u:
                external_urls.append(u)
    
    print()
    print("â”€" * 60)
    print(f"Resume: {resume_path}")
    print(f"External URLs: {external_urls if external_urls else 'None'}")
    print("â”€" * 60)
    print()
    print("ðŸš€ Starting Profile Builder pipeline...\n")
    
    # Build and run the graph
    graph = build_profile_builder_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    initial_state = {
        "resume_file_path": resume_path,
        "external_urls": external_urls,
    }
    
    try:
        final_state = await graph.ainvoke(initial_state, config)
    except Exception as e:
        print(f"\nâŒ Profile Builder failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    if final_state.get("status") != "complete":
        print(f"\nâš ï¸  Pipeline ended with status: {final_state.get('status')}")
        errors = final_state.get("errors", [])
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")
        return None
    
    user_profile = final_state.get("user_profile", {})
    if not user_profile:
        print("\nâŒ No profile generated.")
        return None
    
    print(f"\n{'=' * 60}")
    print(f"  PROFILE BUILDER RESULTS")
    print(f"{'=' * 60}")
    
    display_profile_summary(user_profile)
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "user_profile.json", "w", encoding="utf-8") as f:
        json.dump(user_profile, f, indent=2, ensure_ascii=False)
    print(f"\nðŸ’¾ Profile saved to: {output_dir / 'user_profile.json'}")
    
    return user_profile


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 2: INTERVIEW AGENT (with HITL)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def run_interview(user_profile: dict) -> dict | None:
    """Run the Interview Agent with HITL question loop.
    
    This is where the LangGraph interrupt() pattern comes to life:
    1. We start the graph â€” it runs until the first interrupt()
    2. We read the interrupt payload (the question)
    3. We display it and get the user's answer
    4. We resume the graph with Command(resume=answer)
    5. Repeat until all questions are answered
    6. The graph evaluates answers and updates scores
    
    Returns the updated UserProfile dict or None.
    """
    
    print(f"\n{'=' * 60}")
    print(f"  SAMAS â€” Phase 2: Skill Verification Interview")
    print(f"{'=' * 60}")
    print()
    print("  This interview will test your skills with 7 questions:")
    print("  â€¢ 2 MCQ questions to verify your strongest skills")
    print("  â€¢ 5 written questions to assess skills with lower proof scores")
    print("  â€¢ Each question tests 2-3 related skills at once")
    print()
    print("  Type 'quit' at any time to end the interview early.")
    print()
    
    ready = input("  Ready to begin? (y/n): ").strip().lower()
    if ready not in ("y", "yes", ""):
        print("  Interview skipped.")
        return None
    
    print()
    
    # Build the interview graph
    graph = build_interview_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    initial_state = {
        "user_profile": user_profile,
        "num_questions": 7,
    }
    
    # Start the graph â€” runs until the first interrupt (first question)
    print("ðŸš€ Starting Interview Agent...\n")
    
    try:
        await graph.ainvoke(initial_state, config)
    except Exception as e:
        print(f"\nâŒ Interview Agent failed during startup: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    # â”€â”€â”€â”€ HITL LOOP: Ask questions one at a time locally â”€â”€â”€â”€
    # The graph is now paused at the single interrupt() containing all questions.
    # We loop locally: read question â†’ display â†’ get answer â†’ append to array.
    # Then we resume the graph with the entire array.
    
    early_quit = False
    
    # Check graph state â€” is it still waiting for input?
    snapshot = graph.get_state(config)
    
    if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
        payload = snapshot.tasks[0].interrupts[0].value
        
        if payload.get("type") == "interview_questions":
            questions = payload.get("questions", [])
            answers = []
            
            for q in questions:
                display_interview_question(q)
                answer = input("  Your answer: ").strip()
                
                if answer.lower() in ("quit", "exit", "q"):
                    print("\n  Interview ended early. Keeping original scores.")
                    early_quit = True
                    break
                
                if not answer:
                    answer = "(no answer provided)"
                    
                answers.append({
                    "question_id": q.get("question_id"),
                    "answer": answer
                })
            
            # Resume graph with array of all answers
            if not early_quit:
                print("\n  Evaluating answers... Please wait.")
                try:
                    await graph.ainvoke(Command(resume=answers), config)
                except Exception as e:
                    print(f"\nâŒ Interview evaluation failed: {str(e)}")
                    return None
    
    if early_quit:
        return None
    
    # Get the final state after evaluation
    final_state = graph.get_state(config)
    state_values = final_state.values
    
    interview_summary = state_values.get("interview_summary", {})
    updated_profile = state_values.get("updated_user_profile")
    
    if not updated_profile:
        print("\nâš ï¸  Interview completed but no updated profile generated.")
        return None
    
    # Display results
    display_interview_results(interview_summary, updated_profile)
    
    return updated_profile


from app.agents.job_search_agent import build_job_search_graph

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 3: JOB SEARCH AGENT (with HITL Title Selection)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def run_job_search(user_profile: dict) -> list | None:
    """Run the Job Search Agent with HITL title selection and parallel fan-out."""
    
    print(f"\n{'=' * 60}")
    print(f"  SAMAS â€” Phase 3: Multi-Source Job Search")
    print(f"{'=' * 60}")
    
    graph = build_job_search_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    initial_state = {
        "user_profile": user_profile,
        "location": "India"
    }
    
    print("\nðŸš€ Starting Job Search Agent...")
    try:
        await graph.ainvoke(initial_state, config)
    except Exception as e:
        print(f"\nâŒ Job Search Agent failed during startup: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
        
    snapshot = graph.get_state(config)
    if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
        payload = snapshot.tasks[0].interrupts[0].value
        suggested = payload.get("suggested_titles", [])
        
        print("\n" + "â”€" * 60)
        print("  ðŸŽ¯ Job Title Selection")
        print("â”€" * 60)
        print(f"  Based on your profile, we suggest searching for:")
        for i, t in enumerate(suggested, 1):
            print(f"  {i}. {t}")
            
        print("\n  Press Enter to use these titles, or type your own (comma-separated, max 3).")
        user_input = input("  Titles: ").strip()
        
        if user_input:
            selected_titles = [t.strip() for t in user_input.split(",") if t.strip()]
        else:
            selected_titles = suggested
            
        print(f"  > Continuing with: {', '.join(selected_titles)}")
        print("\n  Executing massive parallel search... Please wait (this takes ~10-20 seconds).")
        
        try:
            await graph.ainvoke(Command(resume={"selected_titles": selected_titles, "location": "India"}), config)
        except Exception as e:
            print(f"\nâŒ Search failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
            
    final_state = graph.get_state(config).values
    jobs = final_state.get("deduplicated_jobs", [])
    
    print("\n" + "=" * 60)
    print("  JOB SEARCH RESULTS")
    print("=" * 60)
    print(f"\n  ðŸŽ‰ Found {len(jobs)} deduplicated jobs across Jooble, SerpAPI, and Remotive.")
    
    for i, job in enumerate(jobs[:10], 1):
        # We handle both dict and Pydantic models here
        if hasattr(job, 'model_dump'):
            job = job.model_dump()
            
        print(f"\n  {i}. {job.get('title', 'N/A')} [{job.get('source', 'unknown')}]")
        print(f"     ðŸ¢ {job.get('company', 'N/A')} | ðŸ“ {job.get('location', 'N/A')}")
        print(f"     ðŸ”— {job.get('url', 'N/A')}")
        
    if len(jobs) > 10:
        print(f"\n  ... and {len(jobs) - 10} more jobs.")
        
    return jobs


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MAIN â€” Orchestrates all agents
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def run_jd_analyzer(jobs, user_profile):
    """Run the JD Analyzer Agent (Phase 4)."""
    if not jobs:
        return {}
        
    print(f"\n{'=' * 60}")
    print(f"  SAMAS â€” Phase 4: JD Analyzer & Ghost Detection")
    print(f"{'=' * 60}")
    
    graph = build_jd_analyzer_graph()
    
    initial_state = {
        "raw_jobs": jobs,
        "user_profile": user_profile,
        "unique_jobs": [],
        "filtered_jobs": [],
        "dropped_jobs": [],
        "similar_job_map": {},
        "job_batches": [],
        "extracted_requirements": {},
        "vector_store_ready": False
    }
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    try:
        final_state = await graph.ainvoke(initial_state, config)
        return final_state
    except Exception as e:
        print(f"\nâŒ JD Analyzer Agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

async def run_matching_agent(jobs, extracted, user_profile):
    """Run the Matching & Ranking Agent (Phase 5)."""
    if not jobs:
        return []
        
    print(f"\n{'=' * 60}")
    print(f"  SAMAS â€” Phase 5: Math Scoring & Ranking")
    print(f"{'=' * 60}")
    
    graph = build_matching_graph()
    
    initial_state = {
        "unique_jobs": jobs,
        "extracted_requirements": extracted,
        "user_profile": user_profile,
        "matched_jobs": []
    }
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    try:
        final_state = await graph.ainvoke(initial_state, config)
        return final_state.get("matched_jobs", [])
    except Exception as e:
        print(f"\nâŒ Matching Agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    """Run the full SAMAS pipeline."""
    
    # â”€â”€ Phase 1: Build the profile â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    user_profile = await run_profile_builder()
    
    if not user_profile:
        return
    
    # â”€â”€ Phase 2: Skill verification interview â”€â”€â”€â”€â”€â”€â”€
    updated_profile = await run_interview(user_profile)
    
    # Save the final profile (either updated or original)
    final_profile = updated_profile or user_profile
    
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    profile_file = output_dir / "user_profile_final.json"
    with open(profile_file, "w", encoding="utf-8") as f:
        json.dump(final_profile, f, indent=2, ensure_ascii=False)
    
    print(f"\nðŸ’¾ Final profile saved to: {profile_file}")
    
    # â”€â”€ Phase 3: Job Search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    jobs = await run_job_search(final_profile)
    
    if not jobs:
        print("No jobs found to analyze. Exiting.")
        return
        
    jobs_file = output_dir / "job_listings.json"
    # Convert models to dicts if needed
    serializable_jobs = [j.model_dump() if hasattr(j, 'model_dump') else j for j in jobs]
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump(serializable_jobs, f, indent=2, ensure_ascii=False)
    print(f"\nðŸ’¾ Jobs saved to: {jobs_file}")
    
    # Convert dicts back to JobListing objects if needed
    job_objects = []
    for j in jobs:
        if isinstance(j, dict):
            job_objects.append(JobListing(**j))
        else:
            job_objects.append(j)
    
    # â”€â”€ Phase 4: JD Analyzer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    analyzer_state = await run_jd_analyzer(job_objects, final_profile)
    unique_jobs = analyzer_state.get("unique_jobs", job_objects)
    extracted = analyzer_state.get("extracted_requirements", {})
    
    # â”€â”€ Phase 5: Matching & Ranking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    matched_jobs = await run_matching_agent(unique_jobs, extracted, final_profile)
    
    if matched_jobs:
        report_file = output_dir / "match_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# SAMAS Match Report\n\n")
            
            for mj in matched_jobs:
                tier_emoji = {"easy_get": "ðŸŸ¢", "best_match": "ðŸŸ¡", "stretch_goal": "ðŸ”´", "filtered": "âŒ", "ghost": "ðŸ‘»"}.get(mj.tier, "âšª")
                f.write(f"## {tier_emoji} {mj.job.title} at {mj.job.company}\n")
                f.write(f"- **Score:** {mj.match_score:.2f} (Tier: {mj.tier})\n")
                f.write(f"- **Location:** {mj.job.location}\n")
                f.write(f"- **Apply URL:** {mj.job.url}\n")
                if mj.jd_requirements.ghost_probability > 0.0:
                    f.write(f"- **Ghost Job Warning:** {mj.jd_requirements.ghost_probability*100:.0f}% ({mj.jd_requirements.ghost_reasoning})\n")
                f.write(f"\n### Gap Analysis\n")
                f.write(f"- **Summary:** {mj.skill_gap_summary}\n")
                if mj.matched_skills:
                    f.write(f"- **Matched:** {', '.join(mj.matched_skills)}\n")
                if mj.missing_skills:
                    f.write(f"- **Missing:** {', '.join(mj.missing_skills)}\n")
                f.write("\n---\n\n")
                
        print(f"\nðŸ“Š Match Report saved to: {report_file}")
        
    print("\nDone! âœ¨")


if __name__ == "__main__":
    asyncio.run(main())

