"""Regression tests for agent.py CLI."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "Agent produced no output"

    data = json.loads(output)

    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"


def test_agent_uses_read_file_tool():
    """Test that agent uses read_file tool for documentation questions."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), "What is the Git workflow for creating a PR?"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "Agent produced no output"

    data = json.loads(output)

    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check that read_file was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"


def test_agent_uses_list_files_tool():
    """Test that agent uses list_files tool for directory listing questions."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), "What files are in the wiki directory?"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "Agent produced no output"

    data = json.loads(output)

    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check that list_files was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files to be called"


def test_agent_uses_query_api_for_framework():
    """Test that agent uses read_file to find backend framework from source code."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), "What Python web framework does the backend use?"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "Agent produced no output"

    data = json.loads(output)

    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check that read_file was used to examine source code
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"

    # Check that answer mentions FastAPI
    assert "FastAPI" in data["answer"], f"Expected 'FastAPI' in answer, got: {data['answer']}"


def test_agent_uses_query_api_for_items():
    """Test that agent uses query_api to get item count from database."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), "How many items are in the database?"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,
    )

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "Agent produced no output"

    data = json.loads(output)

    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check that query_api was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api to be called"
