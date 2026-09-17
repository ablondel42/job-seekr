"""Tests for SQLite job application tracker and deduplication."""

import pytest
from src.tracker import JobTracker


@pytest.fixture
def tracker(tmp_path):
    """Creates an isolated tracker in a temporary directory."""
    db_path = tmp_path / "test_tracker.db"
    return JobTracker(db_path=db_path)


def test_url_normalization():
    """Verify UTM parameters and fragments are stripped during normalization."""
    url = "https://example.com/job/123?utm_source=linkedin&utm_medium=feed&ref=banner#apply"
    clean = JobTracker.normalize_url(url)
    assert clean == "https://example.com/job/123"


def test_add_and_get_job(tracker):
    """Verify adding a job and retrieving it by ID."""
    job_id = tracker.add_job(
        url="https://company.com/careers/lead-eng",
        title="Lead Engineer",
        company="Company Corp",
        location="Remote",
        source="https://news.ycombinator.com/jobs",
        match_score=85,
        match_rationale="Great fit",
        status="discovered",
    )
    assert job_id == 1

    job = tracker.get_job_by_id(job_id)
    assert job is not None
    assert job["title"] == "Lead Engineer"
    assert job["company"] == "Company Corp"
    assert job["match_score"] == 85
    assert job["status"] == "discovered"


def test_deduplication(tracker):
    """Verify is_job_seen returns True for existing jobs."""
    url = "https://acme.org/jobs/456"
    assert not tracker.is_job_seen(url, "Backend Engineer", "Acme")

    tracker.add_job(
        url=url,
        title="Backend Engineer",
        company="Acme",
        match_score=80,
    )

    # Same URL should be recognized as seen
    assert tracker.is_job_seen(url, "Backend Engineer", "Acme")
    # Same URL with tracking params should also be recognized as seen
    assert tracker.is_job_seen(f"{url}?utm_campaign=social", "Backend Engineer", "Acme")


def test_update_status_and_mark_applied(tracker):
    """Verify updating job status and marking as applied."""
    job_id = tracker.add_job(
        url="https://test.com/job/1",
        title="Developer",
        company="DevCo",
        status="drafted",
    )

    # Update status to applied
    tracker.mark_applied(job_id)
    job = tracker.get_job_by_id(job_id)
    assert job["status"] == "applied"


def test_list_jobs_filtering(tracker):
    """Verify filtering jobs by status."""
    tracker.add_job(url="https://a.com/1", title="Job 1", company="A", status="drafted", match_score=90)
    tracker.add_job(url="https://b.com/2", title="Job 2", company="B", status="ignored", match_score=40)
    tracker.add_job(url="https://c.com/3", title="Job 3", company="C", status="drafted", match_score=80)

    drafted_jobs = tracker.list_jobs(status="drafted")
    assert len(drafted_jobs) == 2
    # Ordered by match score descending
    assert drafted_jobs[0]["match_score"] == 90
    assert drafted_jobs[1]["match_score"] == 80

    all_jobs = tracker.list_jobs()
    assert len(all_jobs) == 3
