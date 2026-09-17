"""Job discovery and web search coordinator."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.config import ProfileConfig, SearchConfig
from src.llm_client import LLMClient, LLMClientError
from src.logger import get_logger

logger = get_logger("searcher")


class JobPosting(BaseModel):
    """Represents a discovered job posting."""
    title: str = Field(description="Job title")
    company: str = Field(description="Company or employer name")
    url: str = Field(default="", description="Direct link or source URL for the job")
    location: str = Field(default="Remote", description="Job location or Remote status")
    description: str = Field(default="", description="Summary of requirements and responsibilities")
    source: str = Field(default="web_search", description="Source URL or search channel")


class JobSearcher:
    """Orchestrates job search using LLM web search capabilities and configured target URLs."""

    def __init__(
        self,
        llm_client: LLMClient,
        search_config: SearchConfig,
        profile_config: ProfileConfig,
    ):
        self.llm = llm_client
        self.search_config = search_config
        self.profile = profile_config

    def _build_search_prompt(self) -> str:
        """Constructs prompt instructing LLM to search live web & target URLs for matching jobs."""
        roles_str = ", ".join(self.profile.target_roles)
        locations_str = ", ".join(self.profile.target_locations)
        skills_str = ", ".join(self.profile.skills_keywords) if self.profile.skills_keywords else "General software engineering"

        urls_section = ""
        if self.search_config.search_urls:
            urls_list = "\n".join(f"- {url}" for url in self.search_config.search_urls)
            urls_section = f"""
SPECIFIC TARGET URLS TO SEARCH AND MONITOR:
{urls_list}
Search these portals and job boards for active openings.
"""

        prompt = f"""You are an automated job hunting researcher.
Your task is to search the web for currently active, open job opportunities matching the candidate's criteria.

TARGET CRITERIA:
- Target Roles: {roles_str}
- Locations: {locations_str}
- Key Skills: {skills_str}
{urls_section}
INSTRUCTIONS:
1. Search live web sources, career boards, and the specific target URLs above for open, currently available postings.
2. Find up to {self.search_config.max_jobs_per_run} distinct, relevant job opportunities.
3. For each job, extract:
   - title: exact job title
   - company: hiring company name
   - url: direct link to posting or career page
   - location: job location (e.g. Remote, Paris, Hybrid)
   - description: brief summary of main responsibilities, tech stack, and key requirements
   - source: name of portal, board, or URL where discovered

OUTPUT FORMAT:
You MUST return ONLY a valid JSON array of objects. Do not include markdown preamble or explanations.
Example structure:
[
  {{
    "title": "Senior Python Backend Engineer",
    "company": "Acme Tech",
    "url": "https://example.com/jobs/123",
    "location": "Remote",
    "description": "Building microservices in FastAPI, PostgreSQL, and LLM pipelines.",
    "source": "https://news.ycombinator.com/jobs"
  }}
]
"""
        return prompt.strip()

    def search_jobs(self) -> List[JobPosting]:
        """Executes search and returns parsed list of JobPosting objects."""
        logger.info(
            f"Searching jobs for roles: {self.profile.target_roles} | Locations: {self.profile.target_locations}"
        )
        if self.search_config.search_urls:
            logger.info(f"Targeting {len(self.search_config.search_urls)} specific URLs: {self.search_config.search_urls}")

        prompt = self._build_search_prompt()
        messages = [
            {"role": "system", "content": "You are a professional technical recruitment search assistant with live web search capabilities."},
            {"role": "user", "content": prompt},
        ]

        try:
            data = self.llm.generate_json(messages, temperature=0.2)
            if not isinstance(data, list):
                # If wrapped in a dictionary like {"jobs": [...]}
                if isinstance(data, dict):
                    for key in ("jobs", "postings", "results", "openings"):
                        if key in data and isinstance(data[key], list):
                            data = data[key]
                            break
                    else:
                        raise ValueError(f"Expected JSON list of jobs, received dict: {list(data.keys())}")
                else:
                    raise ValueError(f"Expected JSON list of jobs, got {type(data)}")

            postings: List[JobPosting] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                company = str(item.get("company", "")).strip()
                url = str(item.get("url", "")).strip()

                if not title or not company:
                    continue

                postings.append(
                    JobPosting(
                        title=title,
                        company=company,
                        url=url,
                        location=str(item.get("location", "Remote")).strip(),
                        description=str(item.get("description", "")).strip(),
                        source=str(item.get("source", "web_search")).strip(),
                    )
                )

            logger.info(f"Discovered {len(postings)} job postings from search")
            return postings[:self.search_config.max_jobs_per_run]

        except Exception as e:
            logger.error(f"Failed to perform job search or parse response: {e}")
            raise
