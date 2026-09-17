#!/usr/bin/env python3
"""Job Seekr CLI - Automated job search, matching, and application generator."""

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.pdf_generator import PDFGenerator
from src.runner import JobSeekrRunner
from src.scheduler import run_daemon
from src.tracker import JobTracker


def cmd_run(args: argparse.Namespace) -> int:
    """Executes a single job discovery and drafting cycle."""
    try:
        runner = JobSeekrRunner(config_path=args.config)
        summary = runner.run_cycle(dry_run=args.dry_run)
        print("\n--- Cycle Summary ---")
        print(f"Jobs Discovered : {summary['found']}")
        print(f"New Jobs        : {summary['new']}")
        print(f"Drafted (Saved) : {summary['drafted']}")
        print(f"Ignored (< Min) : {summary['ignored']}")
        print(f"Errors          : {summary['errors']}")
        return 0 if summary["errors"] == 0 else 1
    except Exception as e:
        print(f"Error executing run cycle: {e}", file=sys.stderr)
        return 1


def cmd_daemon(args: argparse.Namespace) -> int:
    """Runs continuous background scheduler."""
    try:
        runner = JobSeekrRunner(config_path=args.config)
        run_daemon(runner, interval_hours=args.interval)
        return 0
    except KeyboardInterrupt:
        print("\nDaemon interrupted by user. Exiting.")
        return 0
    except Exception as e:
        print(f"Fatal error in daemon: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """Lists tracked jobs from the local database."""
    tracker = JobTracker()
    jobs = tracker.list_jobs(status=args.status, limit=args.limit)

    if not jobs:
        print(f"No tracked jobs found (filter status: {args.status or 'ALL'}).")
        return 0

    print(f"\nTracked Applications ({len(jobs)} shown, filter: {args.status or 'ALL'}):")
    header = f"{'ID':<4} | {'Score':<6} | {'Status':<10} | {'Company':<22} | {'Role':<32} | {'Discovered'}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for j in jobs:
        disc = str(j.get("discovered_at", ""))[:10]
        score_str = f"{j.get('match_score', 0)}%"
        company = (j.get("company", "") or "")[:20]
        role = (j.get("title", "") or "")[:30]
        status = j.get("status", "")
        job_id = j.get("id", "")
        print(f"{job_id:<4} | {score_str:<6} | {status:<10} | {company:<22} | {role:<32} | {disc}")

    print("-" * len(header))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Marks a job application as applied."""
    tracker = JobTracker()
    job = tracker.get_job_by_id(args.job_id)
    if not job:
        print(f"Job #{args.job_id} not found.", file=sys.stderr)
        return 1

    success = tracker.mark_applied(args.job_id)
    if success:
        print(f"Job #{args.job_id} ({job.get('title')} at {job.get('company')}) marked as APPLIED!")
        return 0
    else:
        print(f"Failed to update Job #{args.job_id}.", file=sys.stderr)
        return 1


def cmd_test_pdf(args: argparse.Namespace) -> int:
    """Renders a sample resume and cover letter PDF to test ATS PDF generation."""
    pdf_gen = PDFGenerator()
    out_dir = Path("applications/sample_test")
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_resume = """# Alex Morgan
**Senior Software Engineer & AI Architect**  
Email: alex.morgan@example.com | Phone: +1 (555) 019-2834 | San Francisco, CA / Remote  
LinkedIn: linkedin.com/in/alexmorgan | GitHub: github.com/alexmorgan  

---

## Professional Summary
High-impact Senior Engineer with 8+ years architecting scalable cloud systems and production LLM applications. Expert in Python, FastAPI, TypeScript, and modern distributed systems.

---

## Technical Skills
- **Languages:** Python, TypeScript, Go, SQL, Rust
- **Frameworks:** FastAPI, React, Node.js, Pydantic, ReportLab
- **Cloud & AI:** AWS, Docker, Kubernetes, PostgreSQL, Redis, OpenAI API, Vector DBs

---

## Work Experience

### Principal AI Engineer | Vertex Labs (San Francisco, CA)
*2022 - Present*
- Designed end-to-end multi-agent LLM systems reducing document analysis latency by 60%.
- Scaled distributed FastAPI microservices handling 40,000 requests per minute with 99.99% availability.
- Led a team of 6 engineers, setting architectural patterns and automated CI/CD pipelines.

### Senior Backend Engineer | CloudScale Inc.
*2018 - 2022*
- Re-architected monolithic billing engine into event-driven services using PostgreSQL and Kafka.
- Optimized database query throughput by 4x across 50TB of transactional data.
"""

    sample_letter = """# Application for Senior AI Engineer at Vertex Labs

**Alex Morgan**  
San Francisco, CA | alex.morgan@example.com | +1 (555) 019-2834  
Date: 2026-09-17  

**To:** Hiring Team, Vertex Labs  

Dear Hiring Team,

I am writing to express my strong interest in the Senior AI Engineer position at Vertex Labs. Having spent the last several years building distributed backend infrastructure and production-grade LLM applications, I have closely followed Vertex Labs' work in autonomous agent architectures and would love to contribute to your team.

At my previous role, I led the development of multi-agent LLM systems that reduced document processing latency by 60% while maintaining strict data governance. My deep experience with Python, FastAPI, and asynchronous architectures aligns directly with your mission to build robust, scalable intelligence tools.

I welcome the opportunity to discuss how my technical skills and passion for high-scale systems can help accelerate Vertex Labs' roadmap. Thank you for your time and consideration.

Sincerely,  
Alex Morgan
"""

    res_pdf = out_dir / "sample_resume.pdf"
    let_pdf = out_dir / "sample_cover_letter.pdf"

    pdf_gen.markdown_to_pdf(sample_resume, res_pdf, title="Sample Resume")
    pdf_gen.markdown_to_pdf(sample_letter, let_pdf, title="Sample Cover Letter")

    print("Sample PDFs successfully created:")
    print(f"  - Resume       : {res_pdf.resolve()}")
    print(f"  - Cover Letter : {let_pdf.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="job-seekr",
        description="Automated job search, matching, and application generator.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    p_run = subparsers.add_parser("run", help="Run a single search and drafting cycle")
    p_run.add_argument("--config", default="config/config.yaml", help="Path to config file")
    p_run.add_argument("--dry-run", action="store_true", help="Simulate without calling APIs or writing files")

    # Command: daemon
    p_daemon = subparsers.add_parser("daemon", help="Run in continuous background daemon mode")
    p_daemon.add_argument("--config", default="config/config.yaml", help="Path to config file")
    p_daemon.add_argument("--interval", type=float, default=None, help="Check interval in hours (overrides config)")

    # Command: list
    p_list = subparsers.add_parser("list", help="List tracked jobs and applications")
    p_list.add_argument("--status", default=None, help="Filter by status (discovered, drafted, applied, ignored)")
    p_list.add_argument("--limit", type=int, default=30, help="Max jobs to display")

    # Command: apply
    p_apply = subparsers.add_parser("apply", help="Mark an application as applied")
    p_apply.add_argument("job_id", type=int, help="Job ID to mark as applied")

    # Command: test-pdf
    subparsers.add_parser("test-pdf", help="Generate sample resume and cover letter PDFs to test layout")

    return parser


def main() -> int:
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()
    commands = {
        "run": cmd_run,
        "daemon": cmd_daemon,
        "list": cmd_list,
        "apply": cmd_apply,
        "test-pdf": cmd_test_pdf,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        return cmd_fn(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
