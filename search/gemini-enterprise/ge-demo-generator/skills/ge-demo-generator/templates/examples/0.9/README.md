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

The five files containing `[CURRENCY]` (`comparison_matrix.json`,
`detail_modal.json`, `maps_place_card.json`, `profile_analysis_dashboard.json`,
`ranking_table.json`) carry a placeholder instead of a hardcoded symbol, because
the generator builds demos in every currency. `setup_and_deploy.sh` rewrites it
in place — under `adk_agent/app/examples/0.9/`, before the container image is
built — using `CURRENCY_SYMBOL` from `.env` (default `$`), and aborts the deploy
if any occurrence survives. The placeholder must never reach Cloud Run: the
library feeds these files to the model as few-shot examples, so a literal
`[CURRENCY]50,000` teaches the agent to print exactly that.
