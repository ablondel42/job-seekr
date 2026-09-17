"""Tests for JobSearcher and URL targeting."""

from unittest.mock import MagicMock
from src.config import ProfileConfig, SearchConfig
from src.llm_client import LLMClient
from src.searcher import JobPosting, JobSearcher


def test_build_search_prompt_contains_urls():
    """Verify prompt includes target roles and configured search URLs."""
    llm_mock = MagicMock(spec=LLMClient)
    profile = ProfileConfig(
        target_roles=["Backend Architect"],
        target_locations=["Paris"],
        skills_keywords=["FastAPI", "Postgres"],
    )
    search_cfg = SearchConfig(
        search_urls=["https://news.ycombinator.com/jobs", "https://remoteok.com"],
        max_jobs_per_run=5,
    )

    searcher = JobSearcher(llm_mock, search_cfg, profile)
    prompt = searcher._build_search_prompt()

    assert "Backend Architect" in prompt
    assert "Paris" in prompt
    assert "https://news.ycombinator.com/jobs" in prompt
    assert "https://remoteok.com" in prompt


def test_search_jobs_success():
    """Verify parsing LLM returned job list."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.generate_json.return_value = [
        {
            "title": "Python Developer",
            "company": "DataCorp",
            "url": "https://datacorp.com/jobs/1",
            "location": "Remote",
            "description": "Building data APIs.",
            "source": "https://remoteok.com",
        }
    ]

    profile = ProfileConfig(target_roles=["Python Developer"])
    search_cfg = SearchConfig(max_jobs_per_run=5)

    searcher = JobSearcher(llm_mock, search_cfg, profile)
    results = searcher.search_jobs()

    assert len(results) == 1
    assert isinstance(results[0], JobPosting)
    assert results[0].title == "Python Developer"
    assert results[0].company == "DataCorp"
    assert results[0].source == "https://remoteok.com"


def test_search_jobs_ignores_malformed_entries():
    """Verify jobs with missing title or company are omitted."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.generate_json.return_value = [
        {"title": "", "company": "NoTitleCorp"},
        {"title": "Valid Engineer", "company": "ValidCorp", "url": "https://valid.com"},
        {"foo": "bar"},
    ]

    profile = ProfileConfig(target_roles=["Valid Engineer"])
    search_cfg = SearchConfig(max_jobs_per_run=5)

    searcher = JobSearcher(llm_mock, search_cfg, profile)
    results = searcher.search_jobs()

    assert len(results) == 1
    assert results[0].title == "Valid Engineer"
