# Job Seekr

An automated tool to perform web search for jobs matching your resume, skills, location, and configurable target URLs — drafts tailored resumes and cover letters — and saves ATS-friendly PDFs and Markdown files into local folders ready for applying.

---

## Features

- **Targeted Job Search**: Discovers live job opportunities using your local LLM (`localhost:8000`), evaluating custom search queries and a configurable list of target career URLs (e.g., Hacker News Jobs, WeWorkRemotely, RemoteOK, specific company portals).
- **Intelligent Fit Scoring**: Evaluates candidate fit (0–100%) against your master resume with clear rationale, matching skills, and gap analysis. Discards postings below your configured threshold (default: $\ge 70\%$).
- **Tailored Resumes & Cover Letters**: Generates customized resumes and personalized cover letters targeted to the specific requirements of each role without hallucinating past jobs.
- **Pure-Python ATS-Compliant PDFs**: Compiles clean, ATS-scannable PDFs via `reportlab` alongside editable `.md` files without requiring heavy external C-libraries.
- **SQLite Deduplication & Tracker**: Remembers all discovered jobs so postings are never re-evaluated or duplicated across runs. Tracks application statuses (`drafted`, `applied`, `ignored`).
- **Dual Execution Modes**:
  - **Single Run (`run`)**: Perfect for manual triggering or system crontab / macOS launchd.
  - **Daemon Mode (`daemon`)**: Continuous background scheduler checking at your desired hourly interval.
- **Native macOS Notifications**: Sends desktop alerts when new matching applications are drafted and ready for review.
- **Full Test Coverage**: Robust test suite with 29 automated tests covering configuration, tracker, HTTP LLM client, matching, PDF compilation, and pipeline execution.

---

## Directory Structure

```text
job-seekr/
├── config/
│   └── config.yaml          # Target roles, locations, search URLs, thresholds, LLM settings
├── profile/
│   └── resume.md            # Your master resume
├── data/
│   └── job_seekr.db         # SQLite database tracking seen jobs & status
├── applications/            # Generated applications organized by date and company
│   └── YYYY-MM-DD_Company_Role/
│       ├── job_info.md      # Role overview, match score, breakdown
│       ├── resume.md        # Tailored resume in Markdown
│       ├── resume.pdf       # ATS-ready resume PDF
│       ├── cover_letter.md  # Tailored cover letter in Markdown
│       └── cover_letter.pdf # Professional cover letter PDF
├── logs/
│   └── job_seekr.log        # Rotating log file
├── src/
│   ├── config.py            # Pydantic configuration models & validator
│   ├── tracker.py           # SQLite job deduplication & tracking store
│   ├── llm_client.py        # Direct HTTP POST client to localhost:8000
│   ├── searcher.py          # Job discovery & search URL targeter
│   ├── matcher.py           # Match evaluation & fit scoring (0-100%)
│   ├── tailor.py            # Resume & cover letter generator
│   ├── pdf_generator.py     # Pure-Python ATS PDF generator (ReportLab)
│   ├── notifier.py          # macOS desktop notification dispatcher
│   ├── runner.py            # Single-run pipeline orchestrator
│   └── scheduler.py         # Background daemon runner
├── tests/                   # 29 unit and integration tests
├── main.py                  # CLI entrypoint
└── requirements.txt
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Your Profile & Target URLs

Edit `config/config.yaml`:

```yaml
llm:
  endpoint: "http://localhost:8000/v1/chat/completions"
  model: "default"
  timeout_seconds: 120

profile:
  master_resume_path: "profile/resume.md"
  target_roles:
    - "Senior Software Engineer"
    - "Full Stack Developer"
    - "AI Solutions Engineer"
  target_locations:
    - "Remote"
    - "Paris, France"
  skills_keywords:
    - "Python"
    - "TypeScript"
    - "FastAPI"
    - "React"
    - "LLM Agents"

search:
  # Specific portals and boards to monitor
  search_urls:
    - "https://news.ycombinator.com/jobs"
    - "https://weworkremotely.com/categories/remote-back-end-programming-jobs"
    - "https://remoteok.com"
  max_jobs_per_run: 10
  min_match_score: 70

scheduling:
  check_interval_hours: 6
```

Update `profile/resume.md` with your real master resume, background, and skills.

---

## CLI Usage

### Test PDF Generation
Verify ReportLab PDF generation and inspect the visual layout:
```bash
python3 main.py test-pdf
```
Sample PDFs will be created in `applications/sample_test/`.

### Dry Run (Simulation)
Verify configuration and search targets without calling external endpoints or writing files:
```bash
python3 main.py run --dry-run
```

### Single Execution (Cron / Manual)
Run a single search and generation cycle:
```bash
python3 main.py run
```

### Continuous Background Daemon
Run in continuous background mode (checks every $N$ hours as defined in `config.yaml`):
```bash
python3 main.py daemon
```
To override the interval (e.g. check every 4 hours):
```bash
python3 main.py daemon --interval 4
```

### List Tracked Applications
Inspect discovered jobs and their match scores:
```bash
python3 main.py list
```
Filter by status (`drafted`, `applied`, `ignored`):
```bash
python3 main.py list --status drafted
```

### Mark a Job as Applied
Once you submit your application:
```bash
python3 main.py apply <job_id>
```

---

## Setting up macOS Cron (Optional)

If you prefer system cron over the built-in daemon, add an entry to your crontab:

```bash
crontab -e
```

Example (runs every weekday at 9:00 AM):
```cron
0 9 * * 1-5 cd /Users/arnaud/dev/job-seekr && python3 main.py run >> logs/cron.log 2>&1
```

---

## Running Automated Tests

Run the full pytest test suite:

```bash
pytest tests/ -v
```
