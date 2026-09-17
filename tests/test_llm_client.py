"""Tests for direct HTTP LLM client."""

import pytest
import requests
from unittest.mock import MagicMock, patch

from src.llm_client import LLMClient, LLMClientError


def test_extract_json_from_clean_json():
    """Verify parsing clean JSON string."""
    text = '{"name": "test", "score": 90}'
    data = LLMClient.extract_json_from_text(text)
    assert data == {"name": "test", "score": 90}


def test_extract_json_from_markdown_code_fence():
    """Verify parsing JSON wrapped in markdown code blocks."""
    text = """Here is the result:
```json
[
  {"title": "Engineer", "company": "Tech"}
]
```
Let me know if you need more.
"""
    data = LLMClient.extract_json_from_text(text)
    assert isinstance(data, list)
    assert data[0]["title"] == "Engineer"


def test_extract_json_failure_raises_llm_error():
    """Verify non-JSON response raises LLMClientError."""
    text = "Sorry, I could not find any listings."
    with pytest.raises(LLMClientError):
        LLMClient.extract_json_from_text(text)


@patch("requests.Session.post")
def test_chat_completion_success(mock_post):
    """Verify successful chat completion response handling."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "Hello from mock LLM!"}}
        ]
    }
    mock_post.return_value = mock_response

    client = LLMClient(endpoint="http://localhost:8000/v1/chat/completions")
    result = client.chat_completion([{"role": "user", "content": "Hi"}])
    assert result == "Hello from mock LLM!"


@patch("requests.Session.post")
def test_chat_completion_http_error(mock_post):
    """Verify HTTP error raises LLMClientError."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    client = LLMClient(endpoint="http://localhost:8000/v1/chat/completions", max_retries=0)
    with pytest.raises(LLMClientError, match="500"):
        client.chat_completion([{"role": "user", "content": "Hi"}])
