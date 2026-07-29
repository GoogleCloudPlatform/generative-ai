# Evaluation Sets

This directory contains evaluation sets for testing agent behavior using `adk eval`.

## Running Evaluations

```bash
# Run default evalset
agents-cli eval run

# Run specific evalset
agents-cli eval run --evalset tests/eval/evalsets/custom.evalset.json

# Run all evalsets
agents-cli eval run --all
```

## Evalset Format

Each `.evalset.json` follows the ADK evaluation format:

```json
{
  "eval_set_id": "unique_id",
  "name": "Human-readable name",
  "description": "What this evalset tests",
  "eval_cases": [
    {
      "eval_id": "case_id",
      "conversation": [
        {
          "user_content": {
            "parts": [{"text": "User message"}]
          },
          "intermediate_data": {
            "tool_uses": [
              {"name": "tool_name", "args": {"param": "value"}}
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "app_name",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

## Key Fields

- `eval_cases`: Array of test scenarios
- `conversation`: Sequence of user messages
- `intermediate_data.tool_uses`: Expected tool calls (for trajectory matching)
- `session_input`: Initial session state

## Evaluation Metrics

ADK eval measures:

- **tool_trajectory_avg_score**: Are the correct tools called in the right order?
- **response_match_score**: How similar is the response to expected output?

## Creating Custom Evalsets

1. Copy `basic.evalset.json` as a template
2. Add cases based on your `DESIGN_SPEC.md` scenarios
3. Include expected tool calls for capability tests
4. Run `agents-cli eval run --evalset your_evalset.json`

## Tips

- Start with 3-5 representative cases
- Include both happy path and edge cases
- Test each core capability from DESIGN_SPEC.md
- Add cases when you find bugs in production

See [ADK documentation](https://google.github.io/adk-docs/) for advanced evaluation options.
