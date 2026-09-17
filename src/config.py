"""Configuration models and loaders for Job Seekr."""

from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    endpoint: str = Field(
        default="http://localhost:8000/v1/chat/completions",
        description="Full URL to OpenAI-compatible chat completions endpoint",
    )
    model: str = Field(
        default="default",
        description="Model name to pass in the payload",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=600,
        description="Request timeout in seconds",
    )


class ProfileConfig(BaseModel):
    master_resume_path: str = Field(
        default="profile/resume.md",
        description="Path to master resume file",
    )
    target_roles: List[str] = Field(
        default_factory=lambda: ["Software Engineer"],
        description="List of target role titles",
    )
    target_locations: List[str] = Field(
        default_factory=lambda: ["Remote"],
        description="List of target locations",
    )
    skills_keywords: List[str] = Field(
        default_factory=list,
        description="Key skills to prioritize",
    )

    @field_validator("target_roles")
    @classmethod
    def validate_target_roles(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("target_roles list must not be empty")
        return [role.strip() for role in v if role.strip()]


class SearchConfig(BaseModel):
    search_urls: List[str] = Field(
        default_factory=list,
        description="Configurable list of specific job board / career URLs to search",
    )
    query_templates: List[str] = Field(
        default_factory=lambda: ["{role} {location} hiring now"],
        description="Templates to construct search queries",
    )
    max_jobs_per_run: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum jobs to process in a single run",
    )
    min_match_score: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Minimum match percentage required to draft applications",
    )


class SchedulingConfig(BaseModel):
    check_interval_hours: float = Field(
        default=6.0,
        gt=0.0,
        description="Interval between runs in daemon mode (in hours)",
    )


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    log_file: str = Field(default="logs/job_seekr.log")
    max_bytes: int = Field(default=5_242_880)
    backup_count: int = Field(default=5)


class OutputConfig(BaseModel):
    applications_dir: str = Field(
        default="applications",
        description="Directory where tailored job folders are stored",
    )
    notify_macos: bool = Field(
        default=True,
        description="Whether to trigger macOS desktop notifications",
    )


class AppConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: str | Path = "config/config.yaml") -> AppConfig:
    """Loads and validates configuration from a YAML file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file {path}: {e}") from e

    try:
        return AppConfig.model_validate(raw_data)
    except Exception as e:
        raise ValueError(f"Configuration validation error: {e}") from e


def load_master_resume(resume_path: str | Path) -> str:
    """Loads master resume text from markdown or text file."""
    path = Path(resume_path)
    if not path.is_file():
        raise FileNotFoundError(f"Master resume file not found: {path.resolve()}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Master resume file is empty: {path.resolve()}")

    return content
