import httpx
import hashlib
import asyncio
from typing import List
from app.config import SERPAPI_API_KEY
from app.models.job import JobListing

# Common Indian city mappings for SerpAPI (Google Jobs requires specific format)
CITY_LOCATION_MAP = {
    "hyderabad": "Hyderabad, Telangana, India",
    "hydrabad": "Hyderabad, Telangana, India",
    "bengaluru": "Bengaluru, Karnataka, India",
    "bangalore": "Bengaluru, Karnataka, India",
    "mumbai": "Mumbai, Maharashtra, India",
    "delhi": "New Delhi, Delhi, India",
    "new delhi": "New Delhi, Delhi, India",
    "pune": "Pune, Maharashtra, India",
    "chennai": "Chennai, Tamil Nadu, India",
    "kolkata": "Kolkata, West Bengal, India",
    "gurgaon": "Gurugram, Haryana, India",
    "gurugram": "Gurugram, Haryana, India",
    "noida": "Noida, Uttar Pradesh, India",
    "ahmedabad": "Ahmedabad, Gujarat, India",
    "jaipur": "Jaipur, Rajasthan, India",
    "chandigarh": "Chandigarh, India",
    "lucknow": "Lucknow, Uttar Pradesh, India",
    "kochi": "Kochi, Kerala, India",
    "thiruvananthapuram": "Thiruvananthapuram, Kerala, India",
    "indore": "Indore, Madhya Pradesh, India",
    "coimbatore": "Coimbatore, Tamil Nadu, India",
    "nagpur": "Nagpur, Maharashtra, India",
    "visakhapatnam": "Visakhapatnam, Andhra Pradesh, India",
    "bhubaneswar": "Bhubaneswar, Odisha, India",
}

def _resolve_location(location: str) -> str:
    """Resolve a short location name to a fully-qualified SerpAPI location string."""
    if not location:
        return "India"
    
    normalized = location.strip().lower()
    
    # Check our known city map first
    if normalized in CITY_LOCATION_MAP:
        return CITY_LOCATION_MAP[normalized]
    
    # If it already looks qualified (has a comma), use as-is
    if "," in location:
        return location.strip()
    
    # For unknown short names, append ", India" as a reasonable default
    # SerpAPI handles this gracefully for most cases
    return f"{location.strip()}, India"


async def search_serpapi(title: str, location: str = "India", max_pages: int = 3) -> List[JobListing]:
    """Search for jobs using SerpAPI (Google Jobs) and normalize results with pagination."""
    if not SERPAPI_API_KEY:
        print("SerpAPI API key missing. Skipping SerpAPI search.")
        return []
        
    url = "https://serpapi.com/search"
    all_results = []
    next_token = None
    
    # Resolve location to a format SerpAPI understands
    is_remote = location and location.strip().lower() == "remote"
    resolved_location = _resolve_location(location) if not is_remote else None
    
    search_query = title
    if is_remote:
        # For remote, append "remote" to the search query for better results
        search_query = f"{title} remote"
    
    print(f"   SerpAPI: Searching for '{search_query}' in {resolved_location or 'Remote'} (up to {max_pages} pages)...")
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in range(max_pages):
                params = {
                    "engine": "google_jobs",
                    "q": search_query,
                    "api_key": SERPAPI_API_KEY,
                    "hl": "en",
                }
                
                if is_remote:
                    params["ltype"] = "1"
                elif resolved_location:
                    params["location"] = resolved_location
                
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
                    
                    # Try to extract the apply link
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
                
                await asyncio.sleep(0.5)
                
            return all_results
    except Exception as e:
        print(f"Error fetching from SerpAPI for '{title}': {str(e)}")
        return all_results
