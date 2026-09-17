"""Tailors resume and crafts personalized cover letters for specific job opportunities."""

from typing import Optional
from src.llm_client import LLMClient
from src.logger import get_logger
from src.matcher import MatchResult
from src.searcher import JobPosting

logger = get_logger("tailor")


class ApplicationTailor:
    """Generates tailored resumes and custom cover letters in Markdown format."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def tailor_resume(
        self,
        job: JobPosting,
        master_resume: str,
        match_result: Optional[MatchResult] = None,
    ) -> str:
        """Generates a tailored version of the candidate's resume targeting the specific job."""
        logger.info(f"Tailoring resume for {job.title} at {job.company}...")

        skills_focus = ""
        if match_result and match_result.matching_skills:
            skills_focus = f"Prioritize and emphasize these key matching skills: {', '.join(match_result.matching_skills)}"

        prompt = f"""You are an elite career coach and executive resume writer.
Tailor the candidate's master resume specifically for this job posting.

JOB TARGET:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description & Requirements:
{job.description}

{skills_focus}

CANDIDATE'S MASTER RESUME:
{master_resume}

CRITICAL RULES:
1. NEVER fabricate fake work experiences, titles, degrees, or companies. All facts must be grounded in the master resume.
2. Tailor the Professional Summary to speak directly to the value the candidate brings to this role at {job.company}.
3. Reorder and rephrase bullet points in Work Experience to highlight the most relevant achievements and technical challenges that match the job description.
4. Align the Skills section to feature the technologies requested by the employer prominently.
5. Format strictly in clean, ATS-friendly Markdown with standard headers (# Name, ## Professional Summary, ## Technical Skills, ## Work Experience, ## Education).
6. Do NOT include markdown meta-commentary (like 'Here is the tailored resume:'). Return ONLY the markdown resume.
"""
        messages = [
            {"role": "system", "content": "You are a professional resume writer. Output ONLY the tailored markdown resume text."},
            {"role": "user", "content": prompt},
        ]

        try:
            content = self.llm.chat_completion(messages, temperature=0.3)
            return content.strip()
        except Exception as e:
            logger.error(f"Failed to tailor resume: {e}")
            # Fallback to master resume with note
            return f"# Tailored for {job.title} at {job.company}\n\n{master_resume}"

    def tailor_cover_letter(
        self,
        job: JobPosting,
        master_resume: str,
        match_result: Optional[MatchResult] = None,
    ) -> str:
        """Crafts a personalized, compelling cover letter in Markdown."""
        logger.info(f"Crafting cover letter for {job.title} at {job.company}...")

        rationale_note = ""
        if match_result and match_result.rationale:
            rationale_note = f"Key alignment highlights to incorporate: {match_result.rationale}"

        prompt = f"""You are an expert career strategist.
Write a compelling, professional cover letter tailored for this job.

JOB TARGET:
Role: {job.title}
Company: {job.company}
Location: {job.location}
Job Description:
{job.description}

{rationale_note}

CANDIDATE PROFILE (from master resume):
{master_resume}

GUIDELINES:
1. Address the Hiring Team at {job.company}.
2. Tone: Professional, confident, enthusiastic, and direct (avoid generic fluff).
3. Structure:
   - Header: Candidate Name, Contact, Date, Company details.
   - Opening: Hook explaining enthusiasm for {job.company} and why the candidate is applying for {job.title}.
   - Body Paragraph 1: 1-2 major achievements from candidate's past experience directly solving key requirements of this job.
   - Body Paragraph 2: Technical/cultural fit and how candidate's skills will create immediate value for {job.company}.
   - Closing: Call to action requesting an interview, polite sign-off.
4. Output strictly in clean Markdown. Do not include any explanations before or after the letter.
"""
        messages = [
            {"role": "system", "content": "You are an expert career advisor. Output ONLY the markdown cover letter."},
            {"role": "user", "content": prompt},
        ]

        try:
            content = self.llm.chat_completion(messages, temperature=0.4)
            return content.strip()
        except Exception as e:
            logger.error(f"Failed to craft cover letter: {e}")
            return f"""# Application for {job.title} at {job.company}

Dear Hiring Team,

I am writing to express my strong enthusiasm for the {job.title} position at {job.company}. With my background in software engineering, I am confident in my ability to contribute effectively to your team.

Sincerely,
The Candidate
"""
