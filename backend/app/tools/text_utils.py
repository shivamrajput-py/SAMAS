import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def clean_html(raw_html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    
    # Remove HTML tags
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    
    # Replace common HTML entities
    cleantext = cleantext.replace('&nbsp;', ' ')
    cleantext = cleantext.replace('&amp;', '&')
    cleantext = cleantext.replace('&lt;', '<')
    cleantext = cleantext.replace('&gt;', '>')
    
    # Normalize whitespace
    cleantext = re.sub(r'\s+', ' ', cleantext).strip()
    return cleantext


def calculate_text_similarity(texts: List[str]) -> List[List[float]]:
    """
    Calculate pairwise cosine similarity for a list of texts using TF-IDF.
    Returns an NxN matrix of similarity scores (0.0 to 1.0).
    """
    if not texts or len(texts) < 2:
        return [[1.0] * len(texts) for _ in texts]
        
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(texts)
        similarity_matrix = cosine_similarity(tfidf_matrix)
        return similarity_matrix.tolist()
    except Exception as e:
        print(f"Error calculating text similarity: {e}")
        # Fallback: everything is dissimilar
        return [[1.0 if i == j else 0.0 for j in range(len(texts))] for i in range(len(texts))]


def get_similar_company_jobs(jobs: List[Dict], threshold: float = 0.92) -> Dict[str, List[str]]:
    """
    Find jobs from the same company that have highly similar descriptions.
    Returns a dict mapping job_id to a list of highly similar job_ids.
    """
    # Group jobs by company
    company_groups = {}
    for j in jobs:
        c = j.get("company", "").lower().strip()
        if c not in company_groups:
            company_groups[c] = []
        company_groups[c].append(j)
        
    similar_map = {j.get("id"): [] for j in jobs}
    
    for company, comp_jobs in company_groups.items():
        if len(comp_jobs) < 2:
            continue
            
        texts = [j.get("description", "") for j in comp_jobs]
        sim_matrix = calculate_text_similarity(texts)
        
        for i, job1 in enumerate(comp_jobs):
            for j, job2 in enumerate(comp_jobs):
                if i != j and sim_matrix[i][j] > threshold:
                    similar_map[job1.get("id")].append(job2.get("id"))
                    
    return similar_map
