import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric

# Dummy data for testing
DUMMY_RESUME = """
Jane Doe
Software Engineer
Skills: Python, FastAPI, React, TypeScript, Docker, Kubernetes, AWS.
Experience:
- Senior Backend Engineer at TechCorp. Built microservices with FastAPI and deployed on Kubernetes.
- Frontend Developer at WebSolutions. Developed single-page applications using React and TypeScript.
Education: B.S. Computer Science.
"""

EXTRACTED_PROFILE = """
{
    "personal_info": {"full_name": "Jane Doe"},
    "skills_listed": [
        {"name": "Python", "category": "language"},
        {"name": "FastAPI", "category": "framework"},
        {"name": "React", "category": "framework"},
        {"name": "TypeScript", "category": "language"},
        {"name": "Docker", "category": "tool"},
        {"name": "Kubernetes", "category": "tool"},
        {"name": "AWS", "category": "platform"}
    ]
}
"""

GENERATED_QUESTIONS = """
1. How do you handle dependency injection in FastAPI when building microservices?
2. Explain how you orchestrate Docker containers using Kubernetes.
3. What are the key differences between React and TypeScript?
"""

def test_prism_faithfulness():
    """
    Test that PRISM's extracted skills (actual_output) are faithful 
    to the original resume text (retrieval_context).
    """
    test_case = LLMTestCase(
        input="Extract all skills and personal information from this resume.",
        actual_output=EXTRACTED_PROFILE,
        retrieval_context=[DUMMY_RESUME]
    )
    # The FaithfulnessMetric uses an LLM-as-a-judge to ensure no hallucinations.
    metric = FaithfulnessMetric(threshold=0.8)
    
    assert_test(test_case, [metric])


def test_lucid_answer_relevancy():
    """
    Test that LUCID's generated interview questions are highly relevant 
    to the extracted skills.
    """
    test_case = LLMTestCase(
        input=f"Generate 3 technical interview questions based on this profile: {EXTRACTED_PROFILE}",
        actual_output=GENERATED_QUESTIONS
    )
    metric = AnswerRelevancyMetric(threshold=0.7)
    
    assert_test(test_case, [metric])
