#!/usr/bin/env python3
"""
System Agent CLI — Call an LLM with tools (read_file, list_files, query_api) and return a structured JSON answer.

Usage:
    uv run agent.py "How many items are in the database?"

Output:
    {
      "answer": "...",
      "source": "wiki/git-workflow.md#section",
      "tool_calls": [...]
    }
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# Project root for path security
PROJECT_ROOT = Path(__file__).parent.resolve()


class AgentSettings(BaseSettings):
    """Load LLM and backend configuration from environment."""

    # LLM configuration
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base: str = Field(alias="LLM_API_BASE")
    llm_model: str = Field(alias="LLM_MODEL")

    # Backend API configuration
    lms_api_key: str = Field(default="", alias="LMS_API_KEY")
    agent_api_base_url: str = Field(default="http://localhost:42002", alias="AGENT_API_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def load_settings() -> AgentSettings:
    """Load and validate agent settings."""
    # Try to load from .env.agent.secret first
    env_file = PROJECT_ROOT / ".env.agent.secret"
    if env_file.exists():
        return AgentSettings(_env_file=env_file)
    # Fall back to environment variables only
    return AgentSettings()


def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is safe (no directory traversal).

    Returns: (is_valid, error_message)
    """
    if not path:
        return False, "Path cannot be empty"

    if path.startswith("/"):
        return False, "Absolute paths are not allowed"

    if ".." in path:
        return False, "Directory traversal (..) is not allowed"

    full_path = (PROJECT_ROOT / path).resolve()

    try:
        full_path.relative_to(PROJECT_ROOT)
        return True, ""
    except ValueError:
        return False, f"Path '{path}' is outside project directory"


def read_file(path: str) -> dict[str, Any]:
    """
    Read a file from the project repository.

    Args:
        path: Relative path from project root.

    Returns:
        Dict with 'success' and 'content' or 'error' keys.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return {"success": False, "error": error}

    file_path = PROJECT_ROOT / path

    if not file_path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    if not file_path.is_file():
        return {"success": False, "error": f"Not a file: {path}"}

    try:
        content = file_path.read_text(encoding="utf-8")
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": f"Error reading file: {e}"}


def list_files(path: str) -> dict[str, Any]:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root.

    Returns:
        Dict with 'success' and 'entries' or 'error' keys.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return {"success": False, "error": error}

    dir_path = PROJECT_ROOT / path

    if not dir_path.exists():
        return {"success": False, "error": f"Directory not found: {path}"}

    if not dir_path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}"}

    try:
        entries = sorted([entry.name for entry in dir_path.iterdir()])
        return {"success": True, "entries": entries}
    except Exception as e:
        return {"success": False, "error": f"Error listing directory: {e}"}


def query_api(method: str, path: str, body: str | None = None) -> dict[str, Any]:
    """
    Call the backend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., /items/)
        body: Optional JSON request body

    Returns:
        Dict with 'success', 'status_code', and 'body' or 'error' keys.
    """
    api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    api_key = os.environ.get("LMS_API_KEY", "")

    url = f"{api_base.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, data=body or "{}")
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            result = {
                "success": True,
                "status_code": response.status_code,
                "body": response.text,
            }
            return result

    except httpx.TimeoutException:
        return {"success": False, "error": "API request timed out (30s)"}
    except httpx.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Error: {e}"}


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read documentation, code, or config files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory. Use this to discover what files exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app/routers')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to query data or check system status. Use this for questions about database contents, item counts, scores, or API behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, etc.)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST requests"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}

SYSTEM_PROMPT = """You are a system assistant for a software engineering toolkit.
You have access to three tools:

1. `list_files` - List files in a directory
2. `read_file` - Read contents of a file
3. `query_api` - Call the backend API to query data

Tool selection guide:
- For wiki/how-to questions: Use `list_files` to find files, then `read_file` to read them
- For code questions (framework, ports, etc.): Use `read_file` on source code
- For data questions (item count, scores, etc.): Use `query_api`
- For API behavior questions (status codes, errors): Use `query_api`
- For bug diagnosis: Use `query_api` to reproduce the error, then `read_file` to examine source code

When answering:
1. Use the appropriate tool(s) to find the answer
2. Include a source reference if applicable (file path + section anchor)
3. Be concise and accurate
4. Once you have the answer, provide it directly without more tool calls"""


def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool and return the result."""
    if tool_name not in TOOL_FUNCTIONS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    func = TOOL_FUNCTIONS[tool_name]
    return func(**args)


def call_llm_with_tools(
    question: str,
    settings: AgentSettings,
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Call the LLM API with tool support and agentic loop.

    Returns:
        Tuple of (answer, source, tool_calls_list)
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log: list[dict[str, Any]] = []

    for iteration in range(MAX_TOOL_CALLS):
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                if not data.get("choices"):
                    print("Error: No choices in LLM response", file=sys.stderr)
                    sys.exit(1)

                choice = data["choices"][0]
                message = choice["message"]

                # Check if LLM wants to call tools
                tool_calls = message.get("tool_calls")

                if not tool_calls:
                    # No tool calls - LLM provided final answer
                    answer = message.get("content") or ""
                    # Extract source from answer (look for file references)
                    source = extract_source(answer)
                    return answer, source, tool_calls_log

                # Execute tool calls
                for tool_call in tool_calls:
                    if tool_call.get("type") != "function":
                        continue

                    func = tool_call["function"]
                    tool_name = func["name"]
                    tool_args = json.loads(func["arguments"])

                    result = execute_tool(tool_name, tool_args)

                    # Log the tool call
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": format_tool_result(result),
                    })

                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result),
                    })

                # Add the assistant's message with tool calls
                messages.append(message)

        except httpx.TimeoutException:
            print("Error: LLM request timed out (60s)", file=sys.stderr)
            sys.exit(1)
        except httpx.HTTPError as e:
            print(f"Error: HTTP error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Max iterations reached
    answer = "I reached the maximum number of tool calls (10). Based on the information gathered, I couldn't find a complete answer."
    source = ""
    return answer, source, tool_calls_log


def format_tool_result(result: dict[str, Any]) -> str:
    """Format a tool result for logging."""
    if result.get("success"):
        if "content" in result:
            # Truncate long content for logging
            content = result["content"]
            if len(content) > 500:
                content = content[:500] + "... (truncated)"
            return content
        elif "entries" in result:
            return "\n".join(result["entries"])
        elif "body" in result:
            # API response - show status code and truncated body
            status = result.get("status_code", "?")
            body = result["body"]
            if len(body) > 500:
                body = body[:500] + "... (truncated)"
            return f"Status: {status}\nBody: {body}"
    return f"Error: {result.get('error', 'Unknown error')}"


def extract_source(answer: str) -> str:
    """
    Extract source reference from the answer.

    Looks for patterns like 'wiki/file.md' or 'wiki/file.md#section'.
    """
    import re

    # Look for wiki references with optional anchor
    match = re.search(r"(wiki/[\w\-/]+\.md(?:#[\w\-]+)?)", answer)
    if match:
        return match.group(1)

    # Look for lab references
    match = re.search(r"(lab/[\w\-/]+\.md(?:#[\w\-]+)?)", answer)
    if match:
        return match.group(1)

    # Look for backend file references
    match = re.search(r"(backend/[\w\-/]+\.(?:py|yml|yaml|toml)(?:#[\w\-]+)?)", answer)
    if match:
        return match.group(1)

    return ""


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    settings = load_settings()
    answer, source, tool_calls = call_llm_with_tools(question, settings)

    result = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
