"""Tests for candidate-job matching and scoring."""

from unittest.mock import MagicMock
from src.llm_client import LLMClient
from src.matcher import JobMatcher, MatchResult
from src.searcher import JobPosting


def test_evaluate_match_above_threshold():
    """Verify job with score >= min_match_score is marked is_match=True."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.generate_json.return_value = {
        "match_score": 88,
        "matching_skills": ["Python", "FastAPI"],
        "missing_skills": ["Rust"],
        "rationale": "Exceptional fit for backend requirements.",
    }

    job = JobPosting(
        title="Senior Backend Engineer",
        company="FastScale",
        url="https://fastscale.io/job/1",
        description="FastAPI, Python microservices.",
    )

    matcher = JobMatcher(llm_client=llm_mock, min_match_score=70)
    result = matcher.evaluate(job, master_resume="Experience with Python and FastAPI.")

    assert isinstance(result, MatchResult)
    assert result.match_score == 88
    assert result.is_match is True
    assert "Python" in result.matching_skills


def test_evaluate_match_below_threshold():
    """Verify job with score < min_match_score is marked is_match=False."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.generate_json.return_value = {
        "match_score": 45,
        "matching_skills": [],
        "missing_skills": ["C++", "Embedded systems"],
        "rationale": "Candidate lacks low-level firmware experience.",
    }

    job = JobPosting(
        title="Embedded Firmware Engineer",
        company="HardwareTech",
        url="https://hw.com/job/2",
        description="Requires 5+ years C and RTOS.",
    )

    matcher = JobMatcher(llm_client=llm_mock, min_match_score=70)
    result = matcher.evaluate(job, master_resume="Python backend developer.")

    assert result.match_score == 45
    assert result.is_match is False
