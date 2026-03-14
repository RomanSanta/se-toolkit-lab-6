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
    assert "source" in data, "Missing 'source' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check that read_file was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"

    # Check that source references wiki/git-workflow.md
    source = data.get("source", "")
    assert "wiki/git-workflow.md" in source, f"Expected wiki/git-workflow.md in source, got: {source}"


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
