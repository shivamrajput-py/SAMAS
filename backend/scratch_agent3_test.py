import asyncio
import uuid
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.agents.job_search_agent import build_job_search_graph
from langgraph.types import Command

async def test_agent_3():
    print("=== TESTING AGENT 3 (JOB SEARCH) ===")
    
    # Mock user profile
    user_profile = {
        "skills": [
            {"name": "Python", "proof_score": 0.9},
            {"name": "LangGraph", "proof_score": 0.8},
            {"name": "FastAPI", "proof_score": 0.7}
        ],
        "work_experience": [
            {"title": "GenAI Engineer"}
        ]
    }
    
    graph = build_job_search_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "user_profile": user_profile,
        "location": "India", # Default
        "job_listings": []
    }
    
    print("\n1. Running to interrupt (Suggesting Titles)...")
    await graph.ainvoke(initial_state, config)
    
    state = graph.get_state(config)
    if not (state.next and state.tasks and state.tasks[0].interrupts):
        print("Graph did not interrupt!")
        return
        
    interrupt_payload = state.tasks[0].interrupts[0].value
    suggested = interrupt_payload.get("suggested_titles", [])
    print(f"Suggested Titles: {suggested}")
    
    # Pick the first 2 titles to save SerpAPI quota
    selected = suggested[:2]
    print(f"\n2. Resuming with selected titles: {selected}")
    
    # Resume
    await graph.ainvoke(Command(resume={"selected_titles": selected, "location": "India"}), config)
    
    final_state = graph.get_state(config).values
    jobs = final_state.get("deduplicated_jobs", [])
    
    print(f"\n3. Search Complete! Found {len(jobs)} deduplicated jobs.")
    
    # Print the first 5 jobs to check quality
    print("\n--- FIRST 5 JOBS ---")
    for i, job in enumerate(jobs[:5]):
        if isinstance(job, dict):
            print(f"{i+1}. {job.get('title')} @ {job.get('company')} ({job.get('location')}) - {job.get('job_url')}")
        else:
            print(f"{i+1}. {job.title} @ {job.company} ({job.location}) - {job.job_url}")
            
    # Check for duplicates manually just to be sure
    seen = set()
    duplicates = 0
    for job in jobs:
        if isinstance(job, dict):
            key = f"{job.get('title', '').lower()}::{job.get('company', '').lower()}"
        else:
            key = f"{job.title.lower()}::{job.company.lower()}"
        if key in seen:
            duplicates += 1
        seen.add(key)
        
    print(f"\nManual duplicate check found: {duplicates} duplicates.")

if __name__ == "__main__":
    asyncio.run(test_agent_3())
