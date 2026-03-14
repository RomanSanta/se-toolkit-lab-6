# Agent Documentation

## Overview

This project implements a CLI system agent (`agent.py`) that answers questions by calling an LLM API with three tools: `read_file`, `list_files`, and `query_api`. The agent can read documentation, explore the codebase, and query the backend API to answer both static and data-dependent questions.

## Architecture

### LLM Provider

- **Provider:** Qwen Code API (self-hosted on VM)
- **Model:** `qwen3-coder-plus`
- **API Format:** OpenAI-compatible chat completions with tool calling

### Configuration

The agent reads configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` or env |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` or env |
| `LLM_MODEL` | Model name | `.env.agent.secret` or env |
| `LMS_API_KEY` | Backend API authentication | `.env.docker.secret` or env |
| `AGENT_API_BASE_URL` | Backend API base URL | env (default: `http://localhost:42002`) |

**Important:** The autochecker injects its own values for these environment variables during evaluation. Never hardcode API keys or URLs.

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

### `query_api`

Call the backend API to query data or check system status.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, etc.)
- `path` (string, required): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST requests

**Returns:**
```json
{"success": true, "status_code": 200, "body": "..."}
// or
{"success": false, "error": "..."}
```

**Authentication:** Uses `LMS_API_KEY` from environment via `Authorization: Bearer` header.

## Tool Selection Strategy

The system prompt guides the LLM on when to use each tool:

| Question Type | Tool(s) | Example |
|--------------|---------|---------|
| Wiki/how-to | `list_files`, `read_file` | "How do you protect a branch?" |
| Code questions | `read_file` | "What framework does the backend use?" |
| Data queries | `query_api` | "How many items are in the database?" |
| API behavior | `query_api` | "What status code for unauthenticated request?" |
| Bug diagnosis | `query_api`, `read_file` | "Why does /analytics crash?" |

## Usage

### Basic Usage

```bash
uv run agent.py "How many items are in the database?"
```

### Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "backend/app/routers/items.py",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "Status: 200\nBody: [...]"
    }
  ]
}
```

**Fields:**
- `answer` (string): The LLM's final answer
- `source` (string): Reference to the source (file path or API endpoint)
- `tool_calls` (array): All tool calls made during execution

All debug/error output goes to stderr.

### Exit Codes

- `0`: Success
- Non-zero: Error (missing config, network error, timeout, max tool calls reached, etc.)

## Implementation Details

### Dependencies

- `httpx`: HTTP client for LLM API calls and backend queries
- `pydantic`: Data validation
- `pydantic-settings`: Environment variable loading

### System Prompt

The system prompt is critical for correct tool selection. It explicitly tells the LLM:
1. Which tool to use for each question type
2. To stop calling tools once the answer is found
3. To include source references when applicable

### Tool Call Limit

Maximum 10 tool calls per question to prevent infinite loops.

### Timeout

- LLM requests: 60 seconds
- API requests: 30 seconds

## Testing

### Manual Tests

```bash
# Test wiki lookup
uv run agent.py "What are the steps to protect a branch?"

# Test code reading
uv run agent.py "What framework does the backend use?"

# Test API query
uv run agent.py "How many items are in the database?"

# Test bug diagnosis
uv run agent.py "Why does /analytics/completion-rate crash for lab-99?"
```

### Automated Tests

Run the regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

### Benchmark Evaluation

Run the full benchmark:

```bash
uv run run_eval.py
```

## Lessons Learned

Building this agent revealed several key insights:

1. **Tool descriptions matter:** Vague tool descriptions led to the LLM choosing the wrong tool. Being explicit about when to use each tool (e.g., "Use `query_api` for data questions about database contents") dramatically improved accuracy.

2. **Environment variable separation:** Initially confusing `LMS_API_KEY` (backend auth) with `LLM_API_KEY` (LLM auth) caused authentication failures. Clear naming and separate config files helped.

3. **API error handling:** The `query_api` tool needed robust error handling for network issues, timeouts, and non-JSON responses. Returning structured error messages helped the LLM understand what went wrong.

4. **Source extraction:** The `extract_source` function uses regex to find file references in the answer. This works well for wiki files but could be improved for API endpoints.

5. **Iteration is key:** The first version failed 6/10 benchmark questions. After improving tool descriptions and the system prompt, it passed all 10.

## Files

- `agent.py` — Main CLI entry point with agentic loop and three tools
- `.env.agent.secret` — LLM configuration (not committed to git)
- `.env.docker.secret` — Backend API key (not committed to git)
- `plans/task-1.md` — Task 1 implementation plan
- `plans/task-2.md` — Task 2 implementation plan
- `plans/task-3.md` — Task 3 implementation plan
- `AGENT.md` — This documentation
- `tests/test_agent.py` — Regression tests (5 tests)
- `run_eval.py` — Benchmark evaluation script
