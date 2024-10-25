from unittest.mock import AsyncMock, patch

import pytest

from computer_use_demo.tools.computer import (
    ComputerTool,
    ScalingSource,
    ToolError,
    ToolResult,
)


@pytest.fixture
def computer_tool():
    return ComputerTool()


@pytest.mark.asyncio
async def test_computer_tool_mouse_move(computer_tool):
    with patch.object(computer_tool, "shell", new_callable=AsyncMock) as mock_shell:
        mock_shell.return_value = ToolResult(output="Mouse moved")
        result = await computer_tool(action="mouse_move", coordinate=[100, 200])
        mock_shell.assert_called_once_with(
            f"{computer_tool.xdotool} mousemove --sync 100 200"
        )
        assert result.output == "Mouse moved"


@pytest.mark.asyncio
async def test_computer_tool_type(computer_tool):
    with (
        patch.object(computer_tool, "shell", new_callable=AsyncMock) as mock_shell,
        patch.object(
            computer_tool, "screenshot", new_callable=AsyncMock
        ) as mock_screenshot,
    ):
        mock_shell.return_value = ToolResult(output="Text typed")
        mock_screenshot.return_value = ToolResult(base64_image="base64_screenshot")
        result = await computer_tool(action="type", text="Hello, World!")
        assert mock_shell.call_count == 1
        assert "type --delay 12 -- 'Hello, World!'" in mock_shell.call_args[0][0]
        assert result.output == "Text typed"
        assert result.base64_image == "base64_screenshot"


@pytest.mark.asyncio
async def test_computer_tool_screenshot(computer_tool):
    with patch.object(
        computer_tool, "screenshot", new_callable=AsyncMock
    ) as mock_screenshot:
        mock_screenshot.return_value = ToolResult(base64_image="base64_screenshot")
        result = await computer_tool(action="screenshot")
        mock_screenshot.assert_called_once()
        assert result.base64_image == "base64_screenshot"


@pytest.mark.asyncio
async def test_computer_tool_scaling(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.width = 1920
    computer_tool.height = 1080

    # Test scaling from API to computer
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1366, 768)
    assert x == 1920
    assert y == 1080

    # Test scaling from computer to API
    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 1920, 1080)
    assert x == 1366
    assert y == 768

    # Test no scaling when disabled
    computer_tool._scaling_enabled = False
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1366, 768)
    assert x == 1366
    assert y == 768


@pytest.mark.asyncio
async def test_computer_tool_scaling_with_different_aspect_ratio(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.width = 1920
    computer_tool.height = 1200  # 16:10 aspect ratio

    # Test scaling from API to computer
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 1280, 800)
    assert x == 1920
    assert y == 1200

    # Test scaling from computer to API
    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 1920, 1200)
    assert x == 1280
    assert y == 800


@pytest.mark.asyncio
async def test_computer_tool_no_scaling_for_unsupported_resolution(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.width = 4096
    computer_tool.height = 2160

    # Test no scaling for unsupported resolution
    x, y = computer_tool.scale_coordinates(ScalingSource.API, 4096, 2160)
    assert x == 4096
    assert y == 2160

    x, y = computer_tool.scale_coordinates(ScalingSource.COMPUTER, 4096, 2160)
    assert x == 4096
    assert y == 2160


@pytest.mark.asyncio
async def test_computer_tool_scaling_out_of_bounds(computer_tool):
    computer_tool._scaling_enabled = True
    computer_tool.width = 1920
    computer_tool.height = 1080

    # Test scaling from API with out of bounds coordinates
    with pytest.raises(ToolError, match="Coordinates .*, .* are out of bounds"):
        x, y = computer_tool.scale_coordinates(ScalingSource.API, 2000, 1500)


@pytest.mark.asyncio
async def test_computer_tool_invalid_action(computer_tool):
    with pytest.raises(ToolError, match="Invalid action: invalid_action"):
        await computer_tool(action="invalid_action")


@pytest.mark.asyncio
async def test_computer_tool_missing_coordinate(computer_tool):
    with pytest.raises(ToolError, match="coordinate is required for mouse_move"):
        await computer_tool(action="mouse_move")


@pytest.mark.asyncio
async def test_computer_tool_missing_text(computer_tool):
    with pytest.raises(ToolError, match="text is required for type"):
        await computer_tool(action="type")
