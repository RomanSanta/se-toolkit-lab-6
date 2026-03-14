# Agent Documentation

## Overview

This project implements a CLI agent (`agent.py`) that answers questions by calling an LLM API. This is Task 1 of Lab 6 — the foundation for building a full documentation agent with tools in Tasks 2–3.

## Architecture

### LLM Provider

- **Provider:** Qwen Code API (self-hosted on VM)
- **Model:** `qwen3-coder-plus`
- **API Format:** OpenAI-compatible chat completions

### Configuration

The agent reads configuration from `.env.agent.secret`:

```text
LLM_API_KEY=<your-api-key>
LLM_API_BASE=http://<vm-ip>:<port>/v1
LLM_MODEL=qwen3-coder-plus
```

### Flow

```
User question → agent.py → LLM API → JSON answer
```

1. Parse CLI argument (question)
2. Load settings from `.env.agent.secret`
3. Call LLM via HTTP POST to `/chat/completions`
4. Extract answer from response
5. Output JSON to stdout

## Usage

### Basic Usage

```bash
uv run agent.py "What does REST stand for?"
```

### Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

Fields:
- `answer` (string): The LLM's response
- `tool_calls` (array): Empty for Task 1 (populated in Task 2)

All debug/error output goes to stderr.

### Exit Codes

- `0`: Success
- Non-zero: Error (missing config, network error, timeout, etc.)

## Implementation Details

### Dependencies

- `httpx`: HTTP client for LLM API calls
- `pydantic`: Data validation
- `pydantic-settings`: Environment variable loading

### System Prompt

A minimal system prompt instructs the LLM to answer directly without tool calls:

```
You are a helpful assistant. Answer questions directly and concisely.
Do not use tool calls — just provide the answer.
```

### Timeout

The HTTP request has a 60-second timeout to meet the acceptance criteria.

## Testing

### Manual Test

```bash
uv run agent.py "What is 2+2?"
```

Expected output:
```json
{"answer": "2 + 2 = 4.", "tool_calls": []}
```

### Automated Test

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

## Next Steps (Tasks 2–3)

In the next tasks, the agent will be extended with:

1. **Tools:** `read_file`, `list_files`, `query_api`
2. **Agentic loop:** User input → LLM → tool call → execute → feed result → repeat
3. **Domain knowledge:** System prompt with documentation context

## Files

- `agent.py` — Main CLI entry point
- `.env.agent.secret` — LLM configuration (not committed to git)
- `plans/task-1.md` — Implementation plan
- `AGENT.md` — This documentation
