# Option 1: Use index-based mapping (most reliable)
async def _evaluate_resource_relevance(
    self,
    resources: Dict[str, List[Dict[str, Any]]],
    use_cases: List[Dict[str, Any]],
) -> None:
    """Evaluate the relevance of resources for each use case."""
    for use_case in use_cases:
        title = use_case.get("title", "")
        if not title or title not in resources:
            continue

        use_case_resources = resources[title]
        if not use_case_resources:
            continue

        # Define JSON schema with index for reliable mapping
        relevance_schema = {
            "type": "object",
            "properties": {
                "resource_relevance": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "minimum": 0},  # Add index field
                            "title": {"type": "string"},
                            "relevance_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 10,
                            },
                            "relevance_notes": {"type": "string"},
                        },
                        "required": ["index", "title", "relevance_score", "relevance_notes"],
                    },
                }
            },
            "required": ["resource_relevance"],
        }

        # Prepare resources text with explicit indices
        resources_text = "\n\n".join(
            [
                f"RESOURCE {i} (INDEX {i}): {r.get('title', '')}\n"
                + f"URL: {r.get('url', '')}\n"
                + f"Source: {r.get('source', '')}\n"
                + f"Description: {r.get('description', '')}\n"
                + f"Found via query: {r.get('query', '')}"
                for i, r in enumerate(use_case_resources[:10])
            ]
        )

        prompt = f"""
        Evaluate the relevance of the following resources for implementing this AI/Gen AI use case:

        {use_case_text}

        RESOURCES:
        {resources_text}

        For each resource, provide:
        1. The INDEX number of the resource (important for correct mapping)
        2. The title of the resource
        3. A relevance score (1-10, with 10 being most relevant)
        4. Brief notes explaining why the resource is relevant or not relevant

        IMPORTANT: Always include the correct INDEX number for each resource to ensure proper mapping.
        """

        try:
            result = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=relevance_schema,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            relevance_items = result.get("resource_relevance", [])

            # Update resources using index-based mapping
            for item in relevance_items:
                index = item.get("index")
                if index is not None and 0 <= index < len(use_case_resources):
                    use_case_resources[index]["relevance_score"] = item.get("relevance_score", 5)
                    use_case_resources[index]["relevance_notes"] = item.get("relevance_notes", "")

            # Sort and limit resources
            resources[title] = sorted(
                use_case_resources,
                key=lambda r: r.get("relevance_score", 0),
                reverse=True,
            )[:5]

        except Exception as e:
            logger.error(f"Error evaluating resource relevance: {e}")


# Option 2: Use unique composite keys
async def _evaluate_resource_relevance_v2(
    self,
    resources: Dict[str, List[Dict[str, Any]]],
    use_cases: List[Dict[str, Any]],
) -> None:
    """Alternative approach using composite keys for unique identification."""
    for use_case in use_cases:
        title = use_case.get("title", "")
        if not title or title not in resources:
            continue

        use_case_resources = resources[title]
        if not use_case_resources:
            continue

        # Create unique composite keys (title + url + source)
        def make_composite_key(resource):
            return f"{resource.get('title', '')}|{resource.get('url', '')}|{resource.get('source', '')}"

        # Create mapping with composite keys
        key_to_resource = {make_composite_key(r): r for r in use_case_resources}

        # Include composite keys in the prompt
        resources_text = "\n\n".join(
            [
                f"RESOURCE {i + 1}: {r.get('title', '')}\n"
                + f"URL: {r.get('url', '')}\n"
                + f"Source: {r.get('source', '')}\n"
                + f"Description: {r.get('description', '')}\n"
                + f"COMPOSITE_KEY: {make_composite_key(r)}\n"
                + f"Found via query: {r.get('query', '')}"
                for i, r in enumerate(use_case_resources[:10])
            ]
        )

        # Update schema to include composite key
        relevance_schema = {
            "type": "object",
            "properties": {
                "resource_relevance": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "composite_key": {"type": "string"},
                            "title": {"type": "string"},
                            "relevance_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "relevance_notes": {"type": "string"},
                        },
                        "required": ["composite_key", "title", "relevance_score", "relevance_notes"],
                    },
                }
            },
            "required": ["resource_relevance"],
        }

        # Process results using composite keys
        try:
            result = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=relevance_schema,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            relevance_items = result.get("resource_relevance", [])

            for item in relevance_items:
                composite_key = item.get("composite_key", "")
                if composite_key in key_to_resource:
                    key_to_resource[composite_key]["relevance_score"] = item.get("relevance_score", 5)
                    key_to_resource[composite_key]["relevance_notes"] = item.get("relevance_notes", "")

            # Sort and limit
            resources[title] = sorted(
                use_case_resources,
                key=lambda r: r.get("relevance_score", 0),
                reverse=True,
            )[:5]

        except Exception as e:
            logger.error(f"Error evaluating resource relevance: {e}")


# Option 3: Add unique IDs to resources beforehand
def add_unique_ids_to_resources(self, use_case_resources: List[Dict[str, Any]]) -> None:
    """Add unique IDs to resources to enable reliable mapping."""
    for i, resource in enumerate(use_case_resources):
        resource["unique_id"] = f"resource_{i}_{hash(resource.get('url', ''))}"