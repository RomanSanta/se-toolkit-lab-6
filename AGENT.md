# Agent Documentation

## Overview

This project implements a CLI documentation agent (`agent.py`) that answers questions by calling an LLM API with tools. The agent can read files and list directories to find answers in the project documentation.

## Architecture

### LLM Provider

- **Provider:** Qwen Code API (self-hosted on VM)
- **Model:** `qwen3-coder-plus`
- **API Format:** OpenAI-compatible chat completions with tool calling

### Configuration

The agent reads configuration from `.env.agent.secret`:

```text
LLM_API_KEY=<your-api-key>
LLM_API_BASE=http://<vm-ip>:<port>/v1
LLM_MODEL=qwen3-coder-plus
```

### Agentic Loop

```
User question → LLM (with tools) → tool_calls?
    │
    ├─yes→ Execute tools → Append results as "tool" messages → Loop back
    │
    └─no→ Final answer → Extract answer + source → Output JSON
```

1. Send user question + system prompt + tool definitions to LLM
2. Parse response:
   - If `tool_calls` present: execute each tool, append results, repeat (max 10 iterations)
   - If no tool calls: extract answer from message content
3. Output JSON with `answer`, `source`, `tool_calls`

## Tools

### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root

**Returns:**
```json
{"success": true, "content": "..."}
// or
{"success": false, "error": "..."}
```

**Security:** Rejects absolute paths and paths containing `..` (directory traversal).

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root

**Returns:**
```json
{"success": true, "entries": ["file1.md", "file2.md", ...]}
// or
{"success": false, "error": "..."}
```

**Security:** Rejects absolute paths and paths containing `..` (directory traversal).

## Usage

### Basic Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

**Fields:**
- `answer` (string): The LLM's final answer
- `source` (string): Reference to the wiki section (e.g., `wiki/git-workflow.md#section`)
- `tool_calls` (array): All tool calls made during execution

All debug/error output goes to stderr.

### Exit Codes

- `0`: Success
- Non-zero: Error (missing config, network error, timeout, max tool calls reached, etc.)

## Implementation Details

### Dependencies

- `httpx`: HTTP client for LLM API calls
- `pydantic`: Data validation
- `pydantic-settings`: Environment variable loading

### System Prompt

The system prompt instructs the LLM to:

1. Use `list_files` to discover relevant files in directories like `wiki/` or `lab/`
2. Use `read_file` to read the contents of files
3. Find the answer in the file contents
4. Include a source reference in the answer
5. Stop calling tools once the answer is found

### Tool Call Limit

Maximum 10 tool calls per question to prevent infinite loops.

### Timeout

The HTTP request has a 60-second timeout.

## Testing

### Manual Tests

```bash
# Test list_files tool
uv run agent.py "What files are in the wiki directory?"

# Test read_file tool
uv run agent.py "How do you resolve a merge conflict?"
```

### Automated Tests

Run the regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

## Files

- `agent.py` — Main CLI entry point with agentic loop
- `.env.agent.secret` — LLM configuration (not committed to git)
- `plans/task-1.md` — Task 1 implementation plan
- `plans/task-2.md` — Task 2 implementation plan
- `AGENT.md` — This documentation
- `tests/test_agent.py` — Regression tests
