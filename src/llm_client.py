"""Lightweight direct HTTP POST client for OpenAI-compatible LLM endpoints."""

import json
import re
import time
from typing import Any, Dict, List, Optional
import requests

from src.logger import get_logger

logger = get_logger("llm_client")


class LLMClientError(Exception):
    """Base exception for LLM client communication errors."""
    pass


class LLMClient:
    """Sends direct HTTP POST requests to an OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/v1/chat/completions",
        model: str = "default",
        timeout_seconds: int = 120,
        max_retries: int = 2,
    ):
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Sends a chat completion request and returns the assistant's response text."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if extra_payload:
            payload.update(extra_payload)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        last_exception = None
        for attempt in range(1, self.max_retries + 2):
            try:
                logger.debug(f"Sending LLM request to {self.endpoint} (attempt {attempt})")
                response = self.session.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )

                if response.status_code != 200:
                    err_msg = (
                        f"LLM endpoint error {response.status_code}: {response.text[:300]}"
                    )
                    logger.error(err_msg)
                    raise LLMClientError(err_msg)

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMClientError("LLM response contained empty 'choices' list")

                message = choices[0].get("message", {})
                content = message.get("content", "")
                return content.strip()

            except requests.exceptions.ConnectionError as e:
                last_exception = LLMClientError(
                    f"Connection refused at {self.endpoint}. "
                    "Make sure your server is running (e.g. uvicorn): {e}"
                )
                logger.warning(f"Connection failed (attempt {attempt}/{self.max_retries + 1}): {last_exception}")
            except requests.exceptions.Timeout as e:
                last_exception = LLMClientError(
                    f"LLM request timed out after {self.timeout_seconds}s at {self.endpoint}: {e}"
                )
                logger.warning(f"Timeout (attempt {attempt}/{self.max_retries + 1}): {last_exception}")
            except requests.exceptions.RequestException as e:
                last_exception = LLMClientError(f"HTTP request failed: {e}")
                logger.warning(f"Request error (attempt {attempt}/{self.max_retries + 1}): {last_exception}")
            except json.JSONDecodeError as e:
                last_exception = LLMClientError(f"Malformed JSON returned by endpoint: {e}")
                logger.warning(f"JSON decode error: {last_exception}")

            if attempt <= self.max_retries:
                time.sleep(1.5 * attempt)

        raise last_exception or LLMClientError("LLM request failed after retries")

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> Any:
        """Calls the LLM and parses the response as structured JSON."""
        raw_text = self.chat_completion(messages, temperature=temperature)
        return self.extract_json_from_text(raw_text)

    @staticmethod
    def extract_json_from_text(text: str) -> Any:
        """Robustly extracts JSON from LLM output, stripping markdown code fences if present."""
        cleaned = text.strip()

        # Check for ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: find first '{' or '[' and last '}' or ']'
            brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
            if brace_match:
                try:
                    return json.loads(brace_match.group(1))
                except json.JSONDecodeError as e:
                    raise LLMClientError(f"Failed to parse extracted JSON snippet: {e}\nRaw: {text[:200]}") from e

            raise LLMClientError(f"No valid JSON found in LLM response: {text[:200]}")
