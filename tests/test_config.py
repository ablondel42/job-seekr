"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path

from src.config import (
    AppConfig,
    LLMConfig,
    ProfileConfig,
    SearchConfig,
    load_config,
    load_master_resume,
)


def test_default_config_loading():
    """Verify default config.yaml loads without errors."""
    config = load_config("config/config.yaml")
    assert isinstance(config, AppConfig)
    assert config.llm.endpoint.startswith("http://")
    assert len(config.profile.target_roles) > 0
    assert len(config.profile.target_locations) > 0
    assert len(config.search.search_urls) > 0
    assert config.search.min_match_score == 70


def test_missing_config_raises_file_not_found(tmp_path):
    """Verify loading non-existent config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "non_existent.yaml")


def test_invalid_yaml_raises_value_error(tmp_path):
    """Verify invalid YAML raises ValueError."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("llm: [unclosed list", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad_yaml)


def test_empty_target_roles_raises_validation_error():
    """Verify empty target_roles list raises validation error."""
    with pytest.raises(ValueError, match="target_roles list must not be empty"):
        ProfileConfig(target_roles=[])


def test_load_master_resume_success(tmp_path):
    """Verify reading master resume."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Master Resume Content", encoding="utf-8")
    content = load_master_resume(resume_file)
    assert content == "# Master Resume Content"


def test_load_master_resume_missing(tmp_path):
    """Verify error on missing resume."""
    with pytest.raises(FileNotFoundError):
        load_master_resume(tmp_path / "missing.md")


def test_load_master_resume_empty(tmp_path):
    """Verify error on empty resume."""
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("   ", encoding="utf-8")
    with pytest.raises(ValueError, match="is empty"):
        load_master_resume(empty_file)
