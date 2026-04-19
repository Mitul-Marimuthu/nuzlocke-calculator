# Nuzlocke Agent Project

## Architecture
- Agents live in `src/agents`, tools in `src/tools`
- MCP configs in `.mcp/json`
- Sessions manages by `Session Manager` in `src/core`

## Tool Conventions
- Tool name matches exported function
- Always return `{ success, ?data, error }` JSON
- Validate inputs and throw descriptive errors

## Running and Testing
- `pytest` to run local backend mechanics
- `npm run test:agents` - run evals in `test/agents` to work with the frontend
- Use env vars for API keys; never hardcode any
