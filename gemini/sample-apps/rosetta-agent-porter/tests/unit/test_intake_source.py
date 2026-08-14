"""Unit tests for source-URL parsing in app.intake (pure logic, no network).

These lock in the fix for the deploy bug where scheme-less chip URLs like
`github.com/langchain-ai/open_deep_research` were treated as local paths and
failed with "local path not found: /code/github.com/...", and add coverage for
monorepo subdirectory sources. Run:

    uv run pytest tests/unit/test_intake_source.py -q
"""

from app import intake


def test_full_https_url_with_git_suffix():
    info = intake._parse_source("https://github.com/langchain-ai/react-agent.git")
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://github.com/langchain-ai/react-agent"
    assert info["subdir"] is None
    assert info["ref"] is None
    assert info["name"] == "react-agent"


def test_scheme_less_repo_root_is_remote_not_local():
    # The exact form that broke in prod.
    info = intake._parse_source("github.com/langchain-ai/open_deep_research")
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://github.com/langchain-ai/open_deep_research"
    assert info["subdir"] is None
    assert info["name"] == "open_deep_research"


def test_scheme_less_subdir_shorthand():
    info = intake._parse_source(
        "github.com/crewAIInc/crewAI-examples/crews/marketing_strategy"
    )
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://github.com/crewAIInc/crewAI-examples"
    assert info["subdir"] == "crews/marketing_strategy"
    assert info["ref"] is None
    assert info["name"] == "marketing_strategy"


def test_github_tree_url_with_ref_and_nested_subdir():
    info = intake._parse_source(
        "https://github.com/microsoft/autogen/tree/main/python/samples/agentchat_chess_game"
    )
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://github.com/microsoft/autogen"
    assert info["ref"] == "main"
    assert info["subdir"] == "python/samples/agentchat_chess_game"
    assert info["name"] == "agentchat_chess_game"


def test_www_prefix_and_trailing_slash_tolerated():
    info = intake._parse_source("https://www.github.com/owner/repo/")
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://github.com/owner/repo"
    assert info["name"] == "repo"


def test_scp_style_git_url_is_verbatim():
    info = intake._parse_source("git@github.com:owner/repo.git")
    assert info["kind"] == "git"
    assert info["clone_url"] == "git@github.com:owner/repo.git"
    assert info["subdir"] is None
    assert info["name"] == "repo"


def test_unknown_host_with_scheme_is_generic_remote():
    info = intake._parse_source("https://example.com/team/agent.git")
    assert info["kind"] == "git"
    assert info["clone_url"] == "https://example.com/team/agent.git"
    assert info["name"] == "agent"


def test_local_path_still_local():
    info = intake._parse_source("/tmp/some/local/agent")
    assert info["kind"] == "local"
    assert info["path"] == "/tmp/some/local/agent"
    assert info["name"] == "agent"


def test_repo_name_matches_parser_name_for_cache_key_consistency():
    # pipeline.py keys the reuse-cache dir on intake.repo_name(url); it must equal
    # the name clone_repo() derives, or a cached clone would never be reused.
    for url in (
        "https://github.com/langchain-ai/react-agent.git",
        "github.com/langchain-ai/open_deep_research",
        "github.com/crewAIInc/crewAI-examples/crews/marketing_strategy",
        "https://github.com/microsoft/autogen/tree/main/python/samples/agentchat_chess_game",
    ):
        assert intake.repo_name(url) == intake._parse_source(url)["name"]
