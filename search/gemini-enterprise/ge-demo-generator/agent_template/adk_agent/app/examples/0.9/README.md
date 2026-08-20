# A2UI few-shot examples (app-specific)

These JSON files are **not** a copy of the A2UI schema or of the Gemini
Enterprise composite catalog. They are few-shot examples written for this demo
generator, supplied to the `a2ui-agent-sdk` library through its documented
extension point:

```python
A2uiSchemaManager(
    version=VERSION_0_9,
    catalogs=[CatalogConfig.from_path(
        name="ge_composite",
        catalog_path="adk_agent/app/catalogs/gemini_enterprise_composite_catalog.json",
        examples_path="adk_agent/app/examples/0.9",
    )],
    schema_modifiers=[remove_strict_validation],
).generate_system_prompt(..., include_schema=True, include_examples=True, validate_examples=True)
```

The A2UI component schema itself comes from the library plus the composite
catalog (`include_schema=True`), and the library validates every example here at
startup (`validate_examples=True`). The examples teach the model this app's
specific card patterns — the welcome-card structure, suggestion-chip contract,
confirmation and compose flows, dashboard and ranking layouts — which have been
tuned across many releases. Replacing them with the stock examples would change
the agent's rendered output.

The catalog is not vendored here. The generated setup script downloads it into
`adk_agent/app/catalogs/` before the container is built, and every example
names it by URL in `createSurface.catalogId`.

Each message carries `"version": "v0.9"`, and every actionable component sends
`action.event.name` together with a literal `action.event.context.prompt` —
Gemini Enterprise uses that string as the user's chat message, and a card
without it renders a press as "User action triggered".

The five files containing `[CURRENCY]` carry a placeholder that the generated
setup script substitutes with the demo's currency symbol at deploy time.
`validate_examples.py` (repo root of this sample) parses every file with the
placeholder substituted.
