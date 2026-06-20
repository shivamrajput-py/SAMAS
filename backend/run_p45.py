import asyncio
import json
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from app.main import run_jd_analyzer, run_matching_agent
from app.models.job import JobListing

async def run_phase_4_5():
    output_dir = Path("c:/Users/98shi/True Job/backend/output")
    
    # Load Profile
    profile_path = output_dir / "user_profile_final.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        final_profile = json.load(f)
        
    # Load Jobs
    jobs_path = output_dir / "job_listings.json"
    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs_data = json.load(f)
        
    job_objects = [JobListing(**j) for j in jobs_data]
    print(f"Loaded {len(job_objects)} jobs.")
    
    # Phase 4
    analyzer_state = await run_jd_analyzer(job_objects, final_profile)
    unique_jobs = analyzer_state.get("unique_jobs", job_objects)
    extracted = analyzer_state.get("extracted_requirements", {})
    
    # Phase 5
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

if __name__ == "__main__":
    asyncio.run(run_phase_4_5())
