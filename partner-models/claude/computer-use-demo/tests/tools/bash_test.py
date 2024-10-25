import pytest

from computer_use_demo.tools.bash import BashTool, ToolError


@pytest.fixture
def bash_tool():
    return BashTool()


@pytest.mark.asyncio
async def test_bash_tool_restart(bash_tool):
    result = await bash_tool(restart=True)
    assert result.system == "tool has been restarted."

    # Verify the tool can be used after restart
    result = await bash_tool(command="echo 'Hello after restart'")
    assert "Hello after restart" in result.output


@pytest.mark.asyncio
async def test_bash_tool_run_command(bash_tool):
    result = await bash_tool(command="echo 'Hello, World!'")
    assert result.output.strip() == "Hello, World!"
    assert result.error == ""


@pytest.mark.asyncio
async def test_bash_tool_no_command(bash_tool):
    with pytest.raises(ToolError, match="no command provided."):
        await bash_tool()


@pytest.mark.asyncio
async def test_bash_tool_session_creation(bash_tool):
    result = await bash_tool(command="echo 'Session created'")
    assert bash_tool._session is not None
    assert "Session created" in result.output


@pytest.mark.asyncio
async def test_bash_tool_session_reuse(bash_tool):
    result1 = await bash_tool(command="echo 'First command'")
    result2 = await bash_tool(command="echo 'Second command'")

    assert "First command" in result1.output
    assert "Second command" in result2.output


@pytest.mark.asyncio
async def test_bash_tool_session_error(bash_tool):
    result = await bash_tool(command="invalid_command_that_does_not_exist")
    assert "command not found" in result.error


@pytest.mark.asyncio
async def test_bash_tool_non_zero_exit(bash_tool):
    result = await bash_tool(command="bash -c 'exit 1'")
    assert result.error.strip() == ""
    assert result.output.strip() == ""


@pytest.mark.asyncio
async def test_bash_tool_timeout(bash_tool):
    await bash_tool(command="echo 'Hello, World!'")
    bash_tool._session._timeout = 0.1  # Set a very short timeout for testing
    with pytest.raises(
        ToolError,
        match="timed out: bash has not returned in 0.1 seconds and must be restarted",
    ):
        await bash_tool(command="sleep 1")
