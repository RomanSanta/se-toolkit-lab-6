# Task 1 Plan — Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API (self-hosted on VM)

**Model:** `qwen3-coder-plus`

**Rationale:**
- 1000 free requests per day
- Works from Russia without VPN
- Strong tool calling capabilities (needed for Tasks 2–3)
- Already configured in `.env.agent.secret`

**Configuration:**
- `LLM_API_BASE=http://10.93.24.233:42005/v1`
- `LLM_MODEL=qwen3-coder-plus`
- `LLM_API_KEY` stored in `.env.agent.secret`

## Agent Architecture

### Input Flow

```
CLI argument → parse question → call LLM → parse response → output JSON
```

### Components

1. **Environment Loading**
   - Read `.env.agent.secret` using `pydantic-settings` or `python-dotenv`
   - Extract `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **LLM Client**
   - Use `httpx` (already in dependencies) to make HTTP POST requests
   - Endpoint: `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Body: OpenAI-compatible format with `model`, `messages`

3. **Response Parsing**
   - Extract `choices[0].message.content` from LLM response
   - Format as JSON: `{"answer": "<content>", "tool_calls": []}`

4. **Output**
   - Write valid JSON to stdout (single line)
   - All debug/progress logs to stderr
   - Exit code 0 on success

### System Prompt (minimal for Task 1)

A simple prompt instructing the LLM to answer questions directly without tool calls.

### Error Handling

- Timeout: 60 seconds for HTTP request
- Network errors: log to stderr, exit with non-zero code
- Invalid response: log to stderr, exit with non-zero code

## Implementation Steps

1. Create `agent.py` in project root
2. Load environment from `.env.agent.secret`
3. Implement `call_llm(question)` function using `httpx`
4. Parse CLI argument with `sys.argv`
5. Output JSON to stdout, logs to stderr
6. Test with sample questions

## Testing Strategy

- Manual test: `uv run agent.py "What is 2+2?"`
- Verify JSON output has `answer` and `tool_calls` fields
- Create regression test using `subprocess` to run agent and parse output
