#!/usr/bin/env python3
"""
Documentation Agent CLI — Call an LLM with tools and return a structured JSON answer.

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    {
      "answer": "...",
      "source": "wiki/git-workflow.md#resolving-merge-conflicts",
      "tool_calls": [...]
    }
"""

import json
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
    env_file = PROJECT_ROOT / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)

    return AgentSettings(_env_file=env_file)


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


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read documentation, code, or any other file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
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
            "description": "List files and directories in a directory. Use this to discover what files exist in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
}

SYSTEM_PROMPT = """You are a documentation assistant for a software engineering toolkit.
You have access to tools that let you read files and list directories in the project.

When answering questions:
1. Use `list_files` to discover relevant files in directories like 'wiki/' or 'lab/'
2. Use `read_file` to read the contents of files
3. Find the answer in the file contents
4. Include a source reference in your answer: the file path and section anchor (e.g., "wiki/git-workflow.md#resolving-merge-conflicts")
5. Once you have found the answer, provide it directly without more tool calls

Be concise and accurate. Always cite your sources."""


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
                    answer = message.get("content", "")
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
