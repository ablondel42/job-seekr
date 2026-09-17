"""Tests for complete pipeline runner and deduplication flow."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import AppConfig, LLMConfig, ProfileConfig, SearchConfig, OutputConfig
from src.matcher import MatchResult
from src.runner import JobSeekrRunner
from src.searcher import JobPosting
from src.tracker import JobTracker


@pytest.fixture
def test_environment(tmp_path):
    """Sets up an isolated test runner with temporary resume, config, and output dirs."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Test Master Resume\nSkills: Python, React", encoding="utf-8")

    db_file = tmp_path / "test.db"
    apps_dir = tmp_path / "applications"

    config = AppConfig(
        llm=LLMConfig(endpoint="http://localhost:8000/v1/chat/completions"),
        profile=ProfileConfig(
            master_resume_path=str(resume_file),
            target_roles=["Senior Python Engineer"],
        ),
        search=SearchConfig(min_match_score=70),
        output=OutputConfig(
            applications_dir=str(apps_dir),
            notify_macos=False,  # Disable actual OS popups in tests
        ),
    )

    runner = JobSeekrRunner(config=config)
    runner.tracker = JobTracker(db_path=db_file)
    return runner, tmp_path


def test_runner_full_cycle(test_environment):
    """Verify end-to-end execution: 1 job passes threshold, 1 job fails, deduplication works."""
    runner, tmp_path = test_environment

    # Mock searcher to return 2 postings
    job_high = JobPosting(
        title="Senior Python Engineer",
        company="AlphaTech",
        url="https://alphatech.com/jobs/1",
        description="Python backend role.",
    )
    job_low = JobPosting(
        title="Junior Graphic Designer",
        company="DesignStudio",
        url="https://designstudio.com/jobs/2",
        description="Figma and Photoshop.",
    )

    runner.searcher.search_jobs = MagicMock(return_value=[job_high, job_low])

    # Mock matcher
    def mock_evaluate(job, resume):
        if "Python" in job.title:
            return MatchResult(
                job=job,
                match_score=85,
                matching_skills=["Python"],
                rationale="Great fit",
                is_match=True,
            )
        return MatchResult(
            job=job,
            match_score=30,
            rationale="Not relevant",
            is_match=False,
        )

    runner.matcher.evaluate = MagicMock(side_effect=mock_evaluate)

    # Mock tailor
    runner.tailor.tailor_resume = MagicMock(return_value="# Tailored Resume for AlphaTech")
    runner.tailor.tailor_cover_letter = MagicMock(return_value="Dear Hiring Team at AlphaTech...")

    # Execute Cycle 1
    summary1 = runner.run_cycle()
    assert summary1["found"] == 2
    assert summary1["new"] == 2
    assert summary1["drafted"] == 1
    assert summary1["ignored"] == 1
    assert summary1["errors"] == 0

    # Verify drafted files created
    apps_dir = Path(runner.config.output.applications_dir)
    app_folders = list(apps_dir.glob("*_AlphaTech_*"))
    assert len(app_folders) == 1
    draft_folder = app_folders[0]
    assert (draft_folder / "job_info.md").exists()
    assert (draft_folder / "resume.md").exists()
    assert (draft_folder / "resume.pdf").exists()
    assert (draft_folder / "cover_letter.md").exists()
    assert (draft_folder / "cover_letter.pdf").exists()

    # Execute Cycle 2 (Deduplication Check)
    # The same jobs are returned by search, but should be deduplicated
    summary2 = runner.run_cycle()
    assert summary2["found"] == 2
    assert summary2["new"] == 0  # 0 new jobs!
    assert summary2["drafted"] == 0
