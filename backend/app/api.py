from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import os
import sys
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile

# Force UTF-8 encoding for standard output/error to fix Windows emoji printing issues
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver


from app.agents.profile_builder import build_profile_builder_graph
from app.agents.interview_agent import build_interview_graph
from app.agents.job_search_agent import build_job_search_graph
from app.agents.jd_analyzer_agent import build_jd_analyzer_graph
from app.agents.matching_agent import build_matching_graph
from app.models.job import JobListing

app = FastAPI(title="SAMAS API")

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Graph instances
profile_builder_graph = build_profile_builder_graph()
interview_graph = build_interview_graph()
job_search_graph = build_job_search_graph()
jd_graph = build_jd_analyzer_graph()

class URLsPayload(BaseModel):
    urls: List[str]

@app.post("/api/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    urls: Optional[str] = Form(None)
):
    """Phase 1: Profile Builder"""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, DOCX, and TXT are supported.")
        
    # Save uploaded file
    suffix = Path(file.filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    external_urls = []
    if urls:
        try:
            external_urls = json.loads(urls)
        except:
            external_urls = [u.strip() for u in urls.split(",") if u.strip()]

    initial_state = {
        "resume_file_path": tmp_path,
        "external_urls": external_urls,
    }
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    try:
        final_state = await profile_builder_graph.ainvoke(initial_state, config)
        user_profile = final_state.get("user_profile", {})
        
        # Cleanup
        os.unlink(tmp_path)
        
        if not user_profile:
            errors = final_state.get("errors", [])
            err_detail = f"Failed to build profile. Reason: {errors[-1] if errors else 'Unknown error'}"
            raise HTTPException(status_code=500, detail=err_detail)
            
        return {"user_profile": user_profile, "thread_id": config["configurable"]["thread_id"]}
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))

class InterviewStartPayload(BaseModel):
    user_profile: Dict[str, Any]
    api_key: Optional[str] = None
    model_name: Optional[str] = None

@app.post("/api/interview/start")
async def start_interview(payload: InterviewStartPayload):
    """Phase 2a: Generate Questions"""
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "custom_api_key": payload.api_key,
            "custom_model": payload.model_name
        },
        "run_name": "InterviewQuestionAgent"
    }
    
    initial_state = {
        "user_profile": payload.user_profile,
        "questions": [],
        "answers": [],
        "current_question_index": 0
    }
    
    # Run until interrupt (after question generation)
    await interview_graph.ainvoke(initial_state, config)
    
    # Get the state and the interrupt payload
    state = interview_graph.get_state(config)
    if state.next and state.tasks and state.tasks[0].interrupts:
        interrupt_payload = state.tasks[0].interrupts[0].value
        return {
            "thread_id": thread_id,
            "questions": interrupt_payload["questions"]
        }
    
    raise HTTPException(status_code=500, detail="Interview graph did not interrupt as expected.")

class InterviewSubmitPayload(BaseModel):
    thread_id: str
    answers: List[Dict[str, Any]]
    api_key: Optional[str] = None
    model_name: Optional[str] = None

@app.post("/api/interview/submit")
async def submit_interview(payload: InterviewSubmitPayload):
    """Phase 2b: Evaluate Answers"""
    config = {
        "configurable": {
            "thread_id": payload.thread_id,
            "custom_api_key": payload.api_key,
            "custom_model": payload.model_name
        },
        "run_name": "InterviewEvalAgent"
    }
    
    # Resume with answers
    await interview_graph.ainvoke(Command(resume=payload.answers), config)
    
    final_state = interview_graph.get_state(config).values
    
    # Retrieve the updated profile from state
    updated_profile = final_state.get("updated_user_profile", final_state.get("user_profile", {}))
    
    # Extract score adjustments from interview_summary
    summary = final_state.get("interview_summary", {})
    raw_adjustments = summary.get("adjustments", [])
    
    # Map 'reason' to 'reasoning' for the frontend
    mapped_adjustments = []
    for adj in raw_adjustments:
        mapped_adjustments.append({
            **adj,
            "reasoning": adj.get("reason", "")
        })
        
    # Inject into the returned profile object
    updated_profile["score_adjustments"] = mapped_adjustments
    
    return {
        "user_profile": updated_profile,
        "evaluations": final_state.get("evaluations", []),
        "questions": final_state.get("questions", []),
        "answers": final_state.get("answers", [])
    }

class SearchStartPayload(BaseModel):
    user_profile: Dict[str, Any]
    api_key: Optional[str] = None
    model_name: Optional[str] = None

@app.post("/api/search/titles")
async def search_titles(payload: SearchStartPayload):
    """Phase 3a: Suggest Titles"""
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "custom_api_key": payload.api_key,
            "custom_model": payload.model_name
        },
        "run_name": "TitleSuggestAgent"
    }
    
    initial_state = {
        "user_profile": payload.user_profile,
        "location": "India", # Default for now
        "job_listings": []
    }
    
    await job_search_graph.ainvoke(initial_state, config)
    
    state = job_search_graph.get_state(config)
    if state.next and state.tasks and state.tasks[0].interrupts:
        interrupt_payload = state.tasks[0].interrupts[0].value
        return {
            "thread_id": thread_id,
            "suggested_titles": interrupt_payload["suggested_titles"]
        }
        
    raise HTTPException(status_code=500, detail="Search graph did not interrupt as expected.")

from fastapi.responses import StreamingResponse

@app.post("/api/upload_resume/stream")
async def upload_resume_stream(
    file: UploadFile = File(...),
    urls: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None)
):
    """Phase 1: Profile Builder (SSE Stream)"""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, DOCX, and TXT are supported.")
        
    suffix = Path(file.filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    external_urls = []
    if urls:
        try:
            external_urls = json.loads(urls)
        except:
            external_urls = [u.strip() for u in urls.split(",") if u.strip()]

    initial_state = {
        "resume_file_path": tmp_path,
        "external_urls": external_urls,
    }
    
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "custom_api_key": api_key,
            "custom_model": model_name
        },
        "run_name": "ProfileBuilderAgent"
    }
    
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting Profile Builder...'})}\n\n"
            
            async for output in profile_builder_graph.astream(initial_state, config):
                for node_name, state_update in output.items():
                    yield f"data: {json.dumps({'type': 'progress', 'node': node_name})}\n\n"
            
            final_state = profile_builder_graph.get_state(config).values
            user_profile = final_state.get("user_profile", {})
            
            if not user_profile:
                errors = final_state.get("errors", [])
                err_msg = " | ".join(errors) if errors else 'Failed to build profile'
                yield f"data: {json.dumps({'type': 'error', 'message': err_msg})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'complete', 'thread_id': thread_id, 'user_profile': user_profile})}\n\n"
                
        except asyncio.CancelledError:
            print(f"Client disconnected during profile build (thread: {thread_id})")
            raise
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Keep the old one for compatibility or replace it? I will keep the non-streaming ones for now, but the frontend will use the /stream variants.

class SearchExecutePayload(BaseModel):
    thread_id: str
    selected_titles: List[str]
    user_profile: Dict[str, Any]
    location: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None

@app.post("/api/search/execute/stream")
async def execute_search_stream(payload: SearchExecutePayload):
    """Phases 3b, 4, and 5: Search, Analyze, Match (SSE Stream)"""
    config = {
        "configurable": {
            "thread_id": payload.thread_id,
            "custom_api_key": payload.api_key,
            "custom_model": payload.model_name
        },
        "run_name": "JobSearchAgent"
    }
    
    async def event_generator():
        try:
            search_loc = payload.location or payload.user_profile.get("personal_info", {}).get("country", "India")
            
            yield f"data: {json.dumps({'type': 'progress', 'node': 'job_search', 'message': 'Searching job boards...'})}\n\n"
            
            # 1. Resume Phase 3 (SerpAPI)
            async for output in job_search_graph.astream(Command(resume={"selected_titles": payload.selected_titles, "location": search_loc}), config):
                for node_name, state_update in output.items():
                    yield f"data: {json.dumps({'type': 'progress', 'node': node_name})}\n\n"
            
            search_state = job_search_graph.get_state(config).values
            dedup_jobs = search_state.get("deduplicated_jobs", [])
            
            if not dedup_jobs:
                yield f"data: {json.dumps({'type': 'complete', 'matched_jobs': []})}\n\n"
                return
                
            job_objects = []
            for j in dedup_jobs:
                if isinstance(j, dict):
                    job_objects.append(JobListing(**j))
                else:
                    job_objects.append(j)
                    
            yield f"data: {json.dumps({'type': 'progress', 'node': 'jd_analyzer_start', 'message': f'Analyzing {len(job_objects)} jobs...'})}\n\n"
            
            jd_config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()),
                    "custom_api_key": payload.api_key,
                    "custom_model": payload.model_name
                },
                "run_name": "JDAnalyzerAgent"
            }
            jd_initial = {"raw_jobs": job_objects, "user_profile": payload.user_profile, "search_location": search_loc}
            
            async for output in jd_graph.astream(jd_initial, jd_config):
                for node_name, state_update in output.items():
                    yield f"data: {json.dumps({'type': 'progress', 'node': f'analyzer_{node_name}'})}\n\n"
            
            analyzer_state = jd_graph.get_state(jd_config).values
            unique_jobs = analyzer_state.get("unique_jobs", job_objects)
            extracted_reqs = analyzer_state.get("extracted_requirements", {})
            dropped_jobs = analyzer_state.get("dropped_jobs", [])
            
            yield f"data: {json.dumps({'type': 'progress', 'node': 'matching_start', 'message': 'Ranking best matches...'})}\n\n"
            
            # 3. Phase 5: Matching
            match_graph = build_matching_graph()
            match_config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()),
                    "custom_api_key": payload.api_key,
                    "custom_model": payload.model_name
                },
                "run_name": "MatchingAgent"
            }
            match_initial = {
                "unique_jobs": unique_jobs,
                "extracted_requirements": extracted_reqs,
                "user_profile": payload.user_profile,
                "search_location": search_loc
            }
            
            async for output in match_graph.astream(match_initial, match_config):
                for node_name, state_update in output.items():
                    yield f"data: {json.dumps({'type': 'progress', 'node': f'matcher_{node_name}'})}\n\n"
            
            match_state = match_graph.get_state(match_config).values
            matched_jobs = match_state.get("matched_jobs", [])
            
            results = [j.model_dump() if hasattr(j, 'model_dump') else j for j in matched_jobs]
            dropped_results = [j.model_dump() if hasattr(j, 'model_dump') else j for j in dropped_jobs]
            
            yield f"data: {json.dumps({'type': 'complete', 'matched_jobs': results, 'dropped_jobs': dropped_results})}\n\n"
            
        except asyncio.CancelledError:
            print(f"Client disconnected during search stream (thread: {payload.thread_id})")
            raise
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
