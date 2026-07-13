# A2UI few-shot examples (app-specific)

These JSON files are **not** a copy of the A2UI schema or the SDK's built-in
catalog. They are few-shot examples written for this demo generator, supplied
to the `a2ui-agent-sdk` library through its documented extension point:

```python
A2uiSchemaManager(
    version=VERSION_0_8,
    catalogs=[BasicCatalog.get_config(version=VERSION_0_8, examples_path="adk_agent/app/examples/0.8")],
).generate_system_prompt(..., include_schema=True, include_examples=True, validate_examples=True)
```

The A2UI component schema itself comes from the library (`include_schema=True`),
and the library validates every example here at startup
(`validate_examples=True`). The examples teach the model this app's specific
card patterns — the welcome-card structure, suggestion-chip contract,
confirmation and compose flows, dashboard and ranking layouts — which have been
tuned across many releases. Replacing them with the stock examples would change
the agent's rendered output.

The five files containing `[CURRENCY]` carry a placeholder that the generated
setup script substitutes with the demo's currency symbol at deploy time.
`validate_examples.py` (repo root of this sample) parses every file with the
placeholder substituted.
