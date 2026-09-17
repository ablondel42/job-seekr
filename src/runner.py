"""End-to-end pipeline runner for Job Seekr."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import AppConfig, load_config, load_master_resume
from src.llm_client import LLMClient
from src.logger import get_logger, setup_logger
from src.matcher import JobMatcher, MatchResult
from src.notifier import send_macos_notification
from src.pdf_generator import PDFGenerator
from src.searcher import JobPosting, JobSearcher
from src.tracker import JobTracker

logger = get_logger("runner")


def sanitize_filename(name: str) -> str:
    """Sanitizes strings to create clean folder and file names."""
    clean = re.sub(r"[^\w\-_\. ]", "", name)
    clean = re.sub(r"\s+", "_", clean).strip("_")
    return clean[:50] or "job"


class JobSeekrRunner:
    """Orchestrates the complete search, evaluation, tailoring, and document generation pipeline."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        config_path: str | Path = "config/config.yaml",
    ):
        if config is not None:
            self.config = config
        else:
            self.config = load_config(config_path)

        # Initialize logging
        setup_logger(
            level=self.config.logging.level,
            log_file=self.config.logging.log_file,
            max_bytes=self.config.logging.max_bytes,
            backup_count=self.config.logging.backup_count,
        )

        # Components
        self.tracker = JobTracker()
        self.llm = LLMClient(
            endpoint=self.config.llm.endpoint,
            model=self.config.llm.model,
            timeout_seconds=self.config.llm.timeout_seconds,
        )
        self.searcher = JobSearcher(
            llm_client=self.llm,
            search_config=self.config.search,
            profile_config=self.config.profile,
        )
        self.matcher = JobMatcher(
            llm_client=self.llm,
            min_match_score=self.config.search.min_match_score,
        )
        from src.tailor import ApplicationTailor
        self.tailor = ApplicationTailor(llm_client=self.llm)
        self.pdf_generator = PDFGenerator()

    def run_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """Executes a single end-to-end job discovery and drafting cycle."""
        logger.info("=== Starting Job Seekr Automation Cycle ===")
        summary: Dict[str, Any] = {
            "found": 0,
            "new": 0,
            "drafted": 0,
            "ignored": 0,
            "errors": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Load Master Resume
        try:
            master_resume = load_master_resume(self.config.profile.master_resume_path)
            logger.info(f"Loaded master resume from {self.config.profile.master_resume_path}")
        except Exception as e:
            logger.error(f"Cannot proceed without master resume: {e}")
            summary["errors"] += 1
            return summary

        if dry_run:
            logger.info("[DRY-RUN] Simulating pipeline execution without calling APIs or writing files.")
            logger.info(f"[DRY-RUN] Target Roles: {self.config.profile.target_roles}")
            logger.info(f"[DRY-RUN] Target Locations: {self.config.profile.target_locations}")
            logger.info(f"[DRY-RUN] Configured Target URLs: {self.config.search.search_urls}")
            return summary

        # 2. Search for Jobs
        try:
            postings = self.searcher.search_jobs()
            summary["found"] = len(postings)
        except Exception as e:
            logger.error(f"Failed during job search: {e}")
            summary["errors"] += 1
            return summary

        # 3. Deduplicate against Tracker
        new_postings: List[JobPosting] = []
        for post in postings:
            if self.tracker.is_job_seen(post.url, post.title, post.company):
                logger.debug(f"Skipping already seen job: {post.title} at {post.company}")
            else:
                new_postings.append(post)

        summary["new"] = len(new_postings)
        logger.info(f"Found {len(postings)} jobs ({len(new_postings)} new, {len(postings) - len(new_postings)} already tracked)")

        # 4. Evaluate & Tailor Each New Job
        for job in new_postings:
            try:
                match = self.matcher.evaluate(job, master_resume)

                if match.is_match:
                    # Create dedicated application directory
                    date_prefix = datetime.now().strftime("%Y-%m-%d")
                    dir_name = f"{date_prefix}_{sanitize_filename(job.company)}_{sanitize_filename(job.title)}"
                    app_dir = Path(self.config.output.applications_dir) / dir_name
                    app_dir.mkdir(parents=True, exist_ok=True)

                    # 4a. Write job_info.md
                    self._save_job_info(app_dir / "job_info.md", job, match)

                    # 4b. Tailor Resume (Markdown + PDF)
                    resume_md = self.tailor.tailor_resume(job, master_resume, match)
                    resume_md_path = app_dir / "resume.md"
                    resume_md_path.write_text(resume_md, encoding="utf-8")

                    resume_pdf_path = app_dir / "resume.pdf"
                    self.pdf_generator.markdown_to_pdf(
                        markdown_text=resume_md,
                        output_path=resume_pdf_path,
                        title=f"Resume - {job.title} at {job.company}",
                    )

                    # 4c. Tailor Cover Letter (Markdown + PDF)
                    letter_md = self.tailor.tailor_cover_letter(job, master_resume, match)
                    letter_md_path = app_dir / "cover_letter.md"
                    letter_md_path.write_text(letter_md, encoding="utf-8")

                    letter_pdf_path = app_dir / "cover_letter.pdf"
                    self.pdf_generator.markdown_to_pdf(
                        markdown_text=letter_md,
                        output_path=letter_pdf_path,
                        title=f"Cover Letter - {job.title} at {job.company}",
                    )

                    # 4d. Track in DB
                    self.tracker.add_job(
                        url=job.url,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        source=job.source,
                        match_score=match.match_score,
                        match_rationale=match.rationale,
                        status="drafted",
                        application_path=str(app_dir),
                    )
                    summary["drafted"] += 1

                    # 4e. Send macOS notification
                    if self.config.output.notify_macos:
                        send_macos_notification(
                            title=f"New Job Match! ({match.match_score}%)",
                            subtitle=f"{job.title} @ {job.company}",
                            message="Tailored resume and cover letter generated in applications folder.",
                        )
                else:
                    # Below threshold: record as ignored to prevent re-processing
                    self.tracker.add_job(
                        url=job.url,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        source=job.source,
                        match_score=match.match_score,
                        match_rationale=match.rationale,
                        status="ignored",
                    )
                    summary["ignored"] += 1

            except Exception as e:
                logger.error(f"Error processing job {job.title} at {job.company}: {e}")
                summary["errors"] += 1

        logger.info(
            f"=== Cycle Completed: {summary['found']} found, {summary['new']} new, "
            f"{summary['drafted']} drafted, {summary['ignored']} ignored, {summary['errors']} errors ==="
        )
        return summary

    def _save_job_info(self, file_path: Path, job: JobPosting, match: MatchResult) -> None:
        """Writes structured job details and match breakdown to job_info.md."""
        content = f"""# {job.title} - {job.company}

- **Company:** {job.company}
- **Role:** {job.title}
- **Location:** {job.location}
- **URL:** [{job.url}]({job.url})
- **Source:** {job.source}
- **Discovered:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Match Score:** {match.match_score}%

---

## Match Assessment
**Rationale:**  
{match.rationale}

**Matching Skills Identified:**  
{', '.join(match.matching_skills) if match.matching_skills else 'None identified'}

**Potential Skill Gaps:**  
{', '.join(match.missing_skills) if match.missing_skills else 'None identified'}

---

## Original Job Description
{job.description}
"""
        file_path.write_text(content.strip(), encoding="utf-8")
