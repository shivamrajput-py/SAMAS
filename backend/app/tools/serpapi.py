import httpx
import hashlib
import asyncio
from typing import List
from app.config import SERPAPI_API_KEY
from app.models.job import JobListing

async def search_serpapi(title: str, location: str = "India", max_pages: int = 3) -> List[JobListing]:
    """Search for jobs using SerpAPI (Google Jobs) and normalize results with pagination."""
    if not SERPAPI_API_KEY:
        print("⚠️ SerpAPI API key missing. Skipping SerpAPI search.")
        return []
        
    url = "https://serpapi.com/search"
    all_results = []
    next_token = None
    
    print(f"   🔍 SerpAPI: Searching for '{title}' in {location} (up to {max_pages} pages)...")
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in range(max_pages):
                params = {
                    "engine": "google_jobs",
                    "q": title,
                    "location": location,
                    "api_key": SERPAPI_API_KEY,
                    "hl": "en",
                }
                
                if next_token:
                    params["next_page_token"] = next_token
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                jobs_data = data.get("jobs_results", [])
                
                for job in jobs_data:
                    company = job.get("company_name", "Unknown Company")
                    job_title = job.get("title", "Unknown Title")
                    
                    # Generate a stable ID
                    raw_id = f"serpapi_{job.get('job_id', '')}_{job_title}_{company}"
                    job_id = hashlib.md5(raw_id.encode()).hexdigest()
                    
                    # Try to extract the apply link. Prefer source_link (direct) over apply_options
                    apply_url = job.get("source_link", "")
                    if not apply_url:
                        apply_options = job.get("apply_options", [])
                        if apply_options and isinstance(apply_options, list):
                            apply_url = apply_options[0].get("link", "")
                        elif job.get("related_links"):
                            apply_url = job.get("related_links", [{}])[0].get("link", "")
                    
                    # Extract job type
                    extensions = job.get("detected_extensions", {})
                    job_type = extensions.get("schedule_type", None)
                    posted_at = extensions.get("posted_at", None)
                    
                    listing = JobListing(
                        id=job_id,
                        title=job_title,
                        company=company,
                        location=job.get("location", location),
                        description=job.get("description", ""),
                        description_quality="full_text",
                        url=apply_url,
                        job_type=job_type,
                        posted_date=posted_at,
                        source="serpapi",
                        search_title=title
                    )
                    all_results.append(listing)
                
                # Pagination
                pagination = data.get("serpapi_pagination", {})
                next_token = pagination.get("next_page_token")
                
                if not next_token:
                    break
                
                # Slight delay between pages to be polite
                await asyncio.sleep(0.5)
                
            return all_results
    except Exception as e:
        print(f"❌ Error fetching from SerpAPI for '{title}': {str(e)}")
        return all_results
