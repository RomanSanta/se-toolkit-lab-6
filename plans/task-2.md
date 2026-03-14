# Task 2 Plan — The Documentation Agent

## Overview

Extend the Task 1 agent with tools (`read_file`, `list_files`) and an agentic loop to answer questions by reading the project wiki.

## Tool Definitions

### `read_file`

**Purpose:** Read contents of a file from the project repository.

**Schema:**
```json
{
  "name": "read_file",
  "description": "Read a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Use `Path.read_text()` to read file contents
- Security: reject paths containing `..` or absolute paths
- Return error message if file doesn't exist

### `list_files`

**Purpose:** List files and directories at a given path.

**Schema:**
```json
{
  "name": "list_files",
  "description": "List files and directories in a directory",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Use `Path.iterdir()` to list entries
- Security: reject paths containing `..` or absolute paths
- Return newline-separated list of entry names

## Agentic Loop

```
Question → LLM (with tools) → tool_calls?
    │
    ├─yes→ Execute tools → Append results as "tool" messages → Loop back
    │
    └─no→ Final answer → Extract answer + source → Output JSON
```

**Loop logic:**
1. Send user question + system prompt + tool definitions to LLM
2. Parse response:
   - If `tool_calls` present: execute each tool, append results, repeat (max 10 iterations)
   - If no tool calls: extract answer from message content
3. Output JSON with `answer`, `source`, `tool_calls`

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files
2. Use `read_file` to read relevant files
3. Include source reference (file path + section anchor) in the answer
4. Stop calling tools once the answer is found

## Path Security

Both tools will validate paths:
- Reject absolute paths (starting with `/`)
- Reject paths containing `..` (directory traversal)
- Resolve path and verify it's within project root
- Return error message for invalid paths

## Output Format

```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Implementation Steps

1. Define tool schemas for OpenAI function calling
2. Implement `read_file` and `list_files` functions with security checks
3. Add agentic loop with max 10 iterations
4. Update output JSON to include `source` and populated `tool_calls`
5. Update system prompt for wiki navigation
6. Add regression tests
