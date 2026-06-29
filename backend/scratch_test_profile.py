import asyncio
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.agents.profile_builder import build_profile_builder_graph

async def main():
    graph = build_profile_builder_graph()
    with open("dummy_resume.txt", "w", encoding='utf-8') as f:
        f.write("John Doe. Skills: Python")
    initial_state = {"resume_file_path": "dummy_resume.txt", "external_urls": []}
    config = {"configurable": {"thread_id": "test_thread"}}
    final_state = await graph.ainvoke(initial_state, config)
    print("ERRORS:", final_state.get("errors"))
    print("USER_PROFILE:", final_state.get("user_profile"))

if __name__ == "__main__":
    asyncio.run(main())
