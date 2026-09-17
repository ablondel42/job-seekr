"""Job fit evaluation and match scoring engine."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.llm_client import LLMClient
from src.logger import get_logger
from src.searcher import JobPosting

logger = get_logger("matcher")


class MatchResult(BaseModel):
    """Result of evaluating a job against candidate's master resume."""
    job: JobPosting
    match_score: int = Field(ge=0, le=100, description="Match score from 0 to 100")
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    rationale: str = Field(default="")
    is_match: bool = Field(default=False)


class JobMatcher:
    """Evaluates job fit against master resume using LLM scoring."""

    def __init__(self, llm_client: LLMClient, min_match_score: int = 70):
        self.llm = llm_client
        self.min_match_score = min_match_score

    def evaluate(self, job: JobPosting, master_resume: str) -> MatchResult:
        """Compares job posting against resume and computes match score."""
        logger.info(f"Evaluating fit for {job.title} at {job.company}...")

        prompt = f"""You are an expert technical talent assessor.
Evaluate how well the candidate's master resume matches this job opportunity.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description & Requirements:
{job.description}

CANDIDATE'S MASTER RESUME:
{master_resume}

INSTRUCTIONS:
1. Assess the candidate's skills, experience, and seniority against the job requirements.
2. Determine an objective match score from 0 to 100 (where 100 is an exact fit, 70 is strong candidate, <60 has major skill or domain gaps).
3. Identify top matching skills and any missing skills.
4. Provide a concise 2-sentence rationale explaining the score.

OUTPUT FORMAT:
Return ONLY a valid JSON object:
{{
  "match_score": 85,
  "matching_skills": ["Python", "FastAPI", "Distributed Systems"],
  "missing_skills": ["Kubernetes administration"],
  "rationale": "Strong alignment on backend architecture and Python stack. Candidate meets all core requirements."
}}
"""
        messages = [
            {"role": "system", "content": "You are a precise technical hiring evaluator. Always output valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            data = self.llm.generate_json(messages, temperature=0.1)
            raw_score = data.get("match_score", 0)
            try:
                score = int(raw_score)
            except (ValueError, TypeError):
                score = 50
            score = max(0, min(100, score))

            matching_skills = [str(s) for s in data.get("matching_skills", [])]
            missing_skills = [str(s) for s in data.get("missing_skills", [])]
            rationale = str(data.get("rationale", "")).strip()

            is_match = score >= self.min_match_score
            logger.info(
                f"Job: '{job.title}' at {job.company} -> Score: {score}% (Threshold: {self.min_match_score}%) -> Match: {is_match}"
            )

            return MatchResult(
                job=job,
                match_score=score,
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                rationale=rationale,
                is_match=is_match,
            )

        except Exception as e:
            logger.error(f"Error evaluating match for {job.title} at {job.company}: {e}")
            # Fallback result with 0 score on error
            return MatchResult(
                job=job,
                match_score=0,
                matching_skills=[],
                missing_skills=[],
                rationale=f"Evaluation error: {e}",
                is_match=False,
            )
