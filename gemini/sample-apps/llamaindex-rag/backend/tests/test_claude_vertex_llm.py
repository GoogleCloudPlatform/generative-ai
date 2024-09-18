from backend.rag.claude_vertex import ClaudeVertexLLM


def test_claude_vertex_llm():
    llm = ClaudeVertexLLM(
        project_id="sysco-smarter-catalog",
        region="us-east5",
        model_name="claude-3-5-sonnet@20240620",
        max_tokens=1024,
        system_prompt="",
    )

    llm.complete(prompt="Tell me something interesting!")
