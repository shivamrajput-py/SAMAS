"""
Web Scraping Tools â€” Browsing external profiles like ChatGPT does.

This module scrapes GitHub, LinkedIn, portfolio sites, and any other
URL the user provides. It's how we gather evidence for proof scoring
beyond what's written in the resume.

HOW IT WORKS:
    We use two approaches depending on the URL:
    
    1. Jina Reader API (for any URL):
       Prepend "https://r.jina.ai/" to any URL, and it returns clean markdown.
       This is exactly how ChatGPT and Claude "browse" the web.
       Free, no API key needed. Just HTTP GET.
       
    2. GitHub REST API (for GitHub profiles):
       Returns structured JSON â€” repo names, languages, stars, topics.
       More reliable than scraping for structured data.
       Free without a token (60 requests/hour), or 5000/hour with a token.
    
    We use BOTH for GitHub: the API gives us structured repo data,
    and Jina Reader gives us the profile page README content.

WHY NOT JUST USE THE API FOR EVERYTHING?
    - LinkedIn has no public API for profiles
    - Portfolio sites are all custom â€” no standard API exists
    - Jina Reader handles ANY website, making our tool universal
"""

import re
from typing import Dict, List, Optional

import httpx

from app.config import (
    GITHUB_TOKEN,
    JINA_READER_BASE_URL,
    JINA_READER_TIMEOUT,
    MAX_SCRAPED_CONTENT_LENGTH,
    MAX_GITHUB_REPOS,
    APIFY_TOKEN,
)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# JINA READER â€” Universal URL â†’ Markdown converter
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def scrape_url_with_jina(url: str) -> str:
    """Fetch any URL and get clean, readable markdown text.
    
    Uses Jina Reader API â€” the same approach ChatGPT uses to "browse" URLs.
    It fetches the page, strips HTML, and returns clean markdown text.
    
    Args:
        url: Any public URL to scrape
        
    Returns:
        Markdown text of the page content
        
    Example:
        >>> text = await scrape_url_with_jina("https://github.com/username")
        >>> print(text[:100])  # Clean markdown of the GitHub profile page
    """
    jina_url = f"{JINA_READER_BASE_URL}/{url}"
    
    async with httpx.AsyncClient(timeout=JINA_READER_TIMEOUT) as client:
        response = await client.get(
            jina_url,
            headers={
                "Accept": "text/markdown",
                "X-Return-Format": "markdown",
            },
            follow_redirects=True,
        )
        response.raise_for_status()
        
        content = response.text
        
        # Truncate to avoid blowing up the LLM's context window.
        # Most useful info is at the top of the page anyway.
        if len(content) > MAX_SCRAPED_CONTENT_LENGTH:
            content = content[:MAX_SCRAPED_CONTENT_LENGTH] + "\n\n[... content truncated ...]"
        
        return content


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GITHUB API â€” Structured repository and profile data
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _extract_github_username(url: str) -> Optional[str]:
    """Pull the username out of a GitHub URL.
    
    Handles various URL formats:
    - https://github.com/username
    - https://github.com/username/
    - https://www.github.com/username
    - github.com/username
    """
    match = re.search(r"github\.com/([a-zA-Z0-9_-]+)", url)
    if match:
        username = match.group(1)
        # Filter out GitHub's own pages (not user profiles)
        github_reserved = {"features", "pricing", "about", "enterprise", "settings"}
        if username.lower() not in github_reserved:
            return username
    return None


def _build_github_headers() -> dict:
    """Build request headers for the GitHub API.
    
    If we have a personal access token, include it for higher rate limits.
    Without token: 60 requests/hour
    With token: 5,000 requests/hour
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SAMAS-ProfileBuilder",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def get_github_profile_data(github_url: str) -> dict:
    """Fetch structured profile data from GitHub using their REST API.
    
    Returns a clean dict with user info, repositories, and language stats.
    This gives us solid evidence for proof scoring â€” real repos with real code.
    
    Args:
        github_url: GitHub profile URL (e.g. "https://github.com/username")
        
    Returns:
        Dict with keys: username, name, bio, public_repos, followers,
                        languages, repositories (list of dicts)
    """
    username = _extract_github_username(github_url)
    if not username:
        return {"error": f"Could not extract GitHub username from: {github_url}"}
    
    headers = _build_github_headers()
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fetch the user profile
        user_resp = await client.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
        )
        
        if user_resp.status_code != 200:
            return {"error": f"GitHub API returned {user_resp.status_code} for user '{username}'"}
        
        user_data = user_resp.json()
        
        # Fetch repositories (most recently updated first)
        repos_resp = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={
                "sort": "updated",
                "direction": "desc",
                "per_page": MAX_GITHUB_REPOS,
                "type": "owner",  # Only repos they own, not forks
            },
            headers=headers,
        )
        
        repos_data = repos_resp.json() if repos_resp.status_code == 200 else []
    
    # Process repos into clean summaries
    languages_seen = set()
    repo_summaries = []
    
    for repo in repos_data:
        # Skip forks unless they have stars (indicating meaningful contribution)
        if repo.get("fork") and repo.get("stargazers_count", 0) == 0:
            continue
        
        language = repo.get("language")
        if language:
            languages_seen.add(language)
        
        repo_summaries.append({
            "name": repo.get("name", ""),
            "description": repo.get("description") or "No description",
            "language": language or "Unknown",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "topics": repo.get("topics", []),
            "updated_at": repo.get("updated_at", ""),
        })
    
    return {
        "username": username,
        "name": user_data.get("name") or username,
        "bio": user_data.get("bio") or "",
        "public_repos": user_data.get("public_repos", 0),
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "created_at": user_data.get("created_at", ""),
        "languages": sorted(languages_seen),
        "repositories": repo_summaries,
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MAIN SCRAPING FUNCTION â€” Orchestrates all URL scraping
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _classify_url(url: str) -> str:
    """Determine what type of link this is based on the domain.
    
    Returns: 'github', 'linkedin', 'portfolio', or 'other'
    """
    url_lower = url.lower()
    if "github.com" in url_lower:
        return "github"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    else:
        return "portfolio"


async def get_linkedin_apify_data(linkedin_url: str) -> dict:
    """Fetch structured profile data from LinkedIn using Apify.
    
    If APIFY_TOKEN is missing or the request fails, returns an error dict.
    Otherwise returns the structured JSON dataset from the Apify actor.
    """
    if not APIFY_TOKEN:
        return {"error": "APIFY_TOKEN not configured"}
        
    endpoint = f"https://api.apify.com/v2/actors/anchor~linkedin-profile-enrichment/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    # Pass multiple common keys since Apify actors differ in their input schemas
    payload = {
        "urls": [linkedin_url],
        "profileUrls": [linkedin_url],
        "linkedinUrls": [linkedin_url],
        "startUrls": [{"url": linkedin_url}]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client: # Apify runs can take a bit longer
        response = await client.post(endpoint, json=payload)
        if response.status_code not in (200, 201):
            return {"error": f"Apify returned {response.status_code}: {response.text}"}
            
        data = response.json()
        if not data or len(data) == 0:
            return {"error": "Apify returned empty dataset"}
            
        # Returns the first item in the dataset
        return data[0]


async def scrape_external_links(urls: List[str]) -> Dict[str, dict]:
    """Scrape all provided external URLs and return structured results.
    
    For each URL, we determine its type and use the best scraping strategy:
    - GitHub: REST API (structured) + Jina Reader (profile page content)
    - LinkedIn: Apify Actor API (structured)
    - Portfolio/Other: Jina Reader (works on any website)
    
    Args:
        urls: List of URLs to scrape (GitHub, LinkedIn, portfolio, etc.)
        
    Returns:
        Dict mapping URL -> scraped data dict with keys:
        - "type": "github" | "linkedin" | "portfolio"
        - "page_content": markdown text from Jina Reader (or structured JSON string for LinkedIn)
        - "api_data": dict (GitHub and LinkedIn only)
        - "error": str (if scraping failed)
    """
    results = {}
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        link_type = _classify_url(url)
        
        try:
            if link_type == "github":
                api_data = await get_github_profile_data(url)
                
                try:
                    page_content = await scrape_url_with_jina(url)
                except Exception:
                    page_content = ""
                
                results[url] = {
                    "type": "github",
                    "api_data": api_data,
                    "page_content": page_content,
                }
                
            elif link_type == "linkedin":
                # Use Apify to get structured data
                api_data = await get_linkedin_apify_data(url)
                
                # We'll also dump the API data into page_content as a JSON string so the LLM can read it
                # in the standard prompt flow without changing the prompt architecture.
                page_content = ""
                if "error" not in api_data:
                    # Format a nice markdown representation of the LinkedIn data for the LLM
                    page_content = f"# LinkedIn Profile: {api_data.get('full_name', '')}\n"
                    page_content += f"Headline: {api_data.get('headline', '')}\n\n"
                    page_content += f"Summary:\n{api_data.get('summary', '')}\n\n"
                    page_content += f"Skills:\n{', '.join(api_data.get('skills', []))}\n\n"
                    
                    page_content += "Experiences:\n"
                    for exp in api_data.get('experiences', []):
                        page_content += f"- {exp.get('title')} at {exp.get('company')} ({exp.get('starts_at')} - {exp.get('ends_at')})\n"
                        page_content += f"  {exp.get('description', '')}\n"
                        
                results[url] = {
                    "type": "linkedin",
                    "api_data": api_data,
                    "page_content": page_content,
                }
                if "error" in api_data:
                    results[url]["error"] = api_data["error"]
                
            else:
                page_content = await scrape_url_with_jina(url)
                results[url] = {
                    "type": link_type,
                    "page_content": page_content,
                }
                
        except httpx.HTTPStatusError as e:
            results[url] = {
                "type": link_type,
                "error": f"HTTP {e.response.status_code}: Could not access {url}",
            }
        except httpx.TimeoutException:
            results[url] = {
                "type": link_type,
                "error": f"Timeout: {url} took too long to respond",
            }
        except Exception as e:
            results[url] = {
                "type": link_type,
                "error": f"Unexpected error scraping {url}: {str(e)}",
            }
    
    return results
