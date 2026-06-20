"""
Tools for SAMAS agents.

Tools are deterministic functions that agents call â€” they don't use LLMs.
Think of them as the "hands" of the agent: fetch data, parse files, call APIs.

- resume_parser.py â†’ PDF/DOCX text extraction
- web_scraper.py   â†’ Jina Reader + GitHub API for external profile scraping
"""

from app.tools.resume_parser import extract_resume_text
from app.tools.web_scraper import scrape_external_links
