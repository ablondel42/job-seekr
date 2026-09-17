"""Tests for resume tailoring and cover letter drafting."""

from unittest.mock import MagicMock
from src.llm_client import LLMClient
from src.matcher import MatchResult
from src.searcher import JobPosting
from src.tailor import ApplicationTailor


def test_tailor_resume():
    """Verify tailor_resume invokes LLM and returns markdown content."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.chat_completion.return_value = "# Tailored Resume\n\n## Summary\nTailored for Apex."

    tailor = ApplicationTailor(llm_client=llm_mock)
    job = JobPosting(title="Software Engineer", company="Apex Corp", description="Backend engineer")
    result = tailor.tailor_resume(job, master_resume="# Master Resume")

    assert "# Tailored Resume" in result
    assert "Tailored for Apex" in result
    llm_mock.chat_completion.assert_called_once()


def test_tailor_cover_letter():
    """Verify tailor_cover_letter invokes LLM and returns markdown letter."""
    llm_mock = MagicMock(spec=LLMClient)
    llm_mock.chat_completion.return_value = "Dear Hiring Team at Apex Corp,\n\nI am excited to apply..."

    tailor = ApplicationTailor(llm_client=llm_mock)
    job = JobPosting(title="Software Engineer", company="Apex Corp", description="Backend engineer")
    letter = tailor.tailor_cover_letter(job, master_resume="# Master Resume")

    assert "Dear Hiring Team at Apex Corp" in letter
    llm_mock.chat_completion.assert_called_once()
