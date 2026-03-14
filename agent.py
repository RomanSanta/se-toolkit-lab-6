#!/usr/bin/env python3
"""
Agent CLI — Call an LLM and return a structured JSON answer.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    {"answer": "...", "tool_calls": []}
"""

import json
import sys
from pathlib import Path

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Load LLM configuration from .env.agent.secret."""

    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base: str = Field(alias="LLM_API_BASE")
    llm_model: str = Field(alias="LLM_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def load_settings() -> AgentSettings:
    """Load and validate agent settings."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)

    return AgentSettings(_env_file=env_file)


def call_llm(question: str, settings: AgentSettings) -> str:
    """Call the LLM API and return the answer."""
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. "
                    "Answer questions directly and concisely. "
                    "Do not use tool calls — just provide the answer."
                ),
            },
            {"role": "user", "content": question},
        ],
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get("choices"):
                print("Error: No choices in LLM response", file=sys.stderr)
                sys.exit(1)

            answer = data["choices"][0]["message"]["content"]
            return answer

    except httpx.TimeoutException:
        print("Error: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    settings = load_settings()
    answer = call_llm(question, settings)

    result = {
        "answer": answer,
        "tool_calls": [],
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
