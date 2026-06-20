import asyncio
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.config import GITHUB_TOKEN
from app.tools.resume_parser import extract_resume_text
from app.tools.web_scraper import scrape_external_links

async def main():
    print(f"=== SAMAS TOOL TESTING: RAW OUTPUTS ===")
    print(f"GitHub Token Loaded: '{GITHUB_TOKEN}'\n")
    
    # 1. Test Resume Parsing
    resume_path = "C:\\Users\\98shi\\Downloads\\shivamrajput_resume.pdf"
    print(f"ðŸ“„ [1] Parsing Resume: {resume_path}")
    try:
        resume_text = extract_resume_text(resume_path)
        print(f"   âœ“ Extracted {len(resume_text)} characters.\n")
        print("   ðŸ” Snippet (First 800 characters):")
        print("   " + "-" * 60)
        print(resume_text[:800])
        print("   " + "-" * 60)
    except Exception as e:
        print(f"   âœ— Error parsing resume: {e}")

    # 2. Test GitHub API and Jina Reader
    urls = [
        "https://github.com/shivamrajput-py",
        "https://www.linkedin.com/in/shivam-rajput-3928a328a/"
    ]
    print(f"\nðŸ”— [2] Scraping URLs: {urls}\n")
    try:
        scraped_data = await scrape_external_links(urls)
        
        for url, data in scraped_data.items():
            print(f"   URL: {url}")
            
            if "error" in data:
                print(f"   âœ— Error: {data['error']}\n")
                continue
                
            if data.get("type") == "github":
                api_data = data.get("api_data", {})
                print(f"   âœ“ GitHub API: Found user '{api_data.get('name')}' with {api_data.get('public_repos')} repos.")
                print(f"     Languages: {', '.join(api_data.get('languages', []))}")
                
            content = data.get("page_content", "")
            print(f"   âœ“ Jina Reader: Extracted {len(content)} characters.\n")
            print("   ðŸ” Snippet (First 1000 characters):")
            print("   " + "-" * 60)
            print(content[:1000])
            print("   " + "-" * 60 + "\n")
    except Exception as e:
        print(f"   âœ— Error scraping URLs: {e}")

if __name__ == "__main__":
    asyncio.run(main())
