# Task 3 Plan — The System Agent

## Overview

Extend the Task 2 agent with a `query_api` tool to interact with the deployed backend API. This enables answering data-dependent questions and system facts.

## LLM Configuration from Environment Variables

The agent must read all LLM configuration from environment variables (not hardcoded):

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |

## New Tool: `query_api`

### Schema

```json
{
  "name": "query_api",
  "description": "Call the backend API to query data or check system status",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
      "path": {"type": "string", "description": "API path (e.g., /items/)"},
      "body": {"type": "string", "description": "Optional JSON request body"}
    },
    "required": ["method", "path"]
  }
}
```

### Implementation

- Read `LMS_API_KEY` from environment (via `.env.docker.secret`)
- Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
- Use `httpx` to make HTTP requests
- Include `Authorization: Bearer {LMS_API_KEY}` header
- Return JSON string with `status_code` and `body`

### Authentication

The `query_api` tool must use `LMS_API_KEY` for authentication. This is different from `LLM_API_KEY`:
- `LMS_API_KEY` — protects backend endpoints (from `.env.docker.secret`)
- `LLM_API_KEY` — authenticates with LLM provider (from `.env.agent.secret`)

## System Prompt Update

Update the system prompt to guide the LLM on when to use each tool:

1. **Wiki questions** (how-to, workflow): Use `list_files` and `read_file` on `wiki/` directory
2. **System facts** (framework, ports): Use `read_file` on source code or config files
3. **Data queries** (item count, scores): Use `query_api` to query the backend
4. **Bug diagnosis**: Use `query_api` to reproduce the error, then `read_file` to examine source code

## Environment Variables Summary

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `LLM_API_KEY` | LLM authentication | Yes | - |
| `LLM_API_BASE` | LLM endpoint | Yes | - |
| `LLM_MODEL` | LLM model name | Yes | - |
| `LMS_API_KEY` | Backend API authentication | Yes | - |
| `AGENT_API_BASE_URL` | Backend API base URL | No | `http://localhost:42002` |

## Benchmark Strategy

1. Run `uv run run_eval.py` to get initial score
2. Analyze failures:
   - Wrong tool used → improve system prompt
   - Tool error → fix implementation
   - Wrong answer format → adjust prompt
3. Iterate until all 10 questions pass
4. Document lessons learned in `AGENT.md`

## Benchmark Status

**Note:** The LLM API (`http://10.93.24.233:42005/v1`) is currently returning 500 errors. The agent implementation is complete and ready for evaluation once the API is back online.

**To run the benchmark:**
```bash
uv run run_eval.py
```

**Expected behavior:**
- Questions 0-1: Use `read_file` on wiki files
- Questions 2-3: Use `read_file`/`list_files` on source code
- Questions 4-7: Use `query_api` to query backend
- Questions 8-9: Use `read_file` for reasoning (LLM judge on bot)

## Implementation Steps

1. Add `LMS_API_KEY` and `AGENT_API_BASE_URL` to settings
2. Implement `query_api` tool function
3. Register `query_api` in TOOLS schema
4. Update system prompt with tool selection guidance
5. Run `run_eval.py` and iterate
6. Add 2 regression tests
7. Update `AGENT.md` with final architecture and lessons learned
