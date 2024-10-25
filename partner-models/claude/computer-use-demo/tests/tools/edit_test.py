from pathlib import Path
from unittest.mock import patch

import pytest

from computer_use_demo.tools.base import CLIResult, ToolError, ToolResult
from computer_use_demo.tools.edit import EditTool


@pytest.mark.asyncio
async def test_view_command():
    edit_tool = EditTool()

    # Test viewing a file that exists
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "File content"
        result = await edit_tool(command="view", path="/test/file.txt")
        assert isinstance(result, CLIResult)
        assert result.output
        assert "File content" in result.output

    # Test viewing a directory
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ), patch("computer_use_demo.tools.edit.run") as mock_run:
        mock_run.return_value = (None, "file1.txt\nfile2.txt", None)
        result = await edit_tool(command="view", path="/test/dir")
        assert isinstance(result, CLIResult)
        assert result.output
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output

    # Test viewing a file with a specific range
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "Line 1\nLine 2\nLine 3\nLine 4"
        result = await edit_tool(
            command="view", path="/test/file.txt", view_range=[2, 3]
        )
        assert isinstance(result, CLIResult)
        assert result.output
        assert "\n     2\tLine 2\n     3\tLine 3\n" in result.output

    # Test viewing a file with an invalid range
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "Line 1\nLine 2\nLine 3\nLine 4"
        with pytest.raises(ToolError, match="Invalid `view_range`"):
            await edit_tool(command="view", path="/test/file.txt", view_range=[3, 2])

    # Test viewing a non-existent file
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ToolError, match="does not exist"):
            await edit_tool(command="view", path="/nonexistent/file.txt")

    # Test viewing a directory with a view_range
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ):
        with pytest.raises(ToolError, match="view_range` parameter is not allowed"):
            await edit_tool(command="view", path="/test/dir", view_range=[1, 2])


@pytest.mark.asyncio
async def test_create_command():
    edit_tool = EditTool()

    # Test creating a new file with content
    with patch("pathlib.Path.exists", return_value=False), patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        result = await edit_tool(
            command="create", path="/test/newfile.txt", file_text="New file content"
        )
        assert isinstance(result, ToolResult)
        assert result.output
        assert "File created successfully" in result.output
        mock_write_text.assert_called_once_with("New file content")

    # Test attempting to create a file without content
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ToolError, match="Parameter `file_text` is required"):
            await edit_tool(command="create", path="/test/newfile.txt")

    # Test attempting to create a file that already exists
    with patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(ToolError, match="File already exists"):
            await edit_tool(
                command="create", path="/test/existingfile.txt", file_text="Content"
            )


@pytest.mark.asyncio
async def test_str_replace_command():
    edit_tool = EditTool()

    # Test replacing a unique string in a file
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Original content"
        result = await edit_tool(
            command="str_replace",
            path="/test/file.txt",
            old_str="Original",
            new_str="New",
        )
        assert isinstance(result, CLIResult)
        assert result.output
        assert "has been edited" in result.output
        mock_write_text.assert_called_once_with("New content")

    # Test attempting to replace a non-existent string
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "Original content"
        with pytest.raises(ToolError, match="did not appear verbatim"):
            await edit_tool(
                command="str_replace",
                path="/test/file.txt",
                old_str="Nonexistent",
                new_str="New",
            )

    # Test attempting to replace a string that appears multiple times
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "Test test test"
        with pytest.raises(ToolError, match="Multiple occurrences"):
            await edit_tool(
                command="str_replace",
                path="/test/file.txt",
                old_str="test",
                new_str="example",
            )

    edit_tool._file_history.clear()
    # Verify that the file history is updated after replacement
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ):
        mock_read_text.return_value = "Original content"
        await edit_tool(
            command="str_replace",
            path="/test/file.txt",
            old_str="Original",
            new_str="New",
        )
        assert edit_tool._file_history[Path("/test/file.txt")] == ["Original content"]


@pytest.mark.asyncio
async def test_insert_command():
    edit_tool = EditTool()

    # Test inserting a string at a valid line number
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Line 1\nLine 2\nLine 3"
        result = await edit_tool(
            command="insert", path="/test/file.txt", insert_line=2, new_str="New Line"
        )
        assert isinstance(result, CLIResult)
        assert result.output
        assert "has been edited" in result.output
        mock_write_text.assert_called_once_with("Line 1\nLine 2\nNew Line\nLine 3")

    # Test inserting a string at the beginning of the file (line 0)
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Line 1\nLine 2"
        result = await edit_tool(
            command="insert",
            path="/test/file.txt",
            insert_line=0,
            new_str="New First Line",
        )
        assert isinstance(result, CLIResult)
        assert result.output
        assert "has been edited" in result.output
        mock_write_text.assert_called_once_with("New First Line\nLine 1\nLine 2")

    # Test inserting a string at the end of the file
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Line 1\nLine 2"
        result = await edit_tool(
            command="insert",
            path="/test/file.txt",
            insert_line=2,
            new_str="New Last Line",
        )
        assert isinstance(result, CLIResult)
        assert result.output
        assert "has been edited" in result.output
        mock_write_text.assert_called_once_with("Line 1\nLine 2\nNew Last Line")

    # Test attempting to insert at an invalid line number
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = "Line 1\nLine 2"
        with pytest.raises(ToolError, match="Invalid `insert_line` parameter"):
            await edit_tool(
                command="insert",
                path="/test/file.txt",
                insert_line=5,
                new_str="Invalid Line",
            )

    # Verify that the file history is updated after insertion
    edit_tool._file_history.clear()
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ):
        mock_read_text.return_value = "Original content"
        await edit_tool(
            command="insert", path="/test/file.txt", insert_line=1, new_str="New Line"
        )
        assert edit_tool._file_history[Path("/test/file.txt")] == ["Original content"]


@pytest.mark.asyncio
async def test_undo_edit_command():
    edit_tool = EditTool()

    # Test undoing a str_replace operation
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Original content"
        await edit_tool(
            command="str_replace",
            path="/test/file.txt",
            old_str="Original",
            new_str="New",
        )
        mock_read_text.return_value = "New content"
        result = await edit_tool(command="undo_edit", path="/test/file.txt")
        assert isinstance(result, CLIResult)
        assert result.output
        assert "Last edit to /test/file.txt undone successfully" in result.output
        mock_write_text.assert_called_with("Original content")

    # Test undoing an insert operation
    edit_tool._file_history.clear()
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ), patch("pathlib.Path.read_text") as mock_read_text, patch(
        "pathlib.Path.write_text"
    ) as mock_write_text:
        mock_read_text.return_value = "Line 1\nLine 2"
        await edit_tool(
            command="insert", path="/test/file.txt", insert_line=1, new_str="New Line"
        )
        mock_read_text.return_value = "Line 1\nNew Line\nLine 2"
        result = await edit_tool(command="undo_edit", path="/test/file.txt")
        assert isinstance(result, CLIResult)
        assert result.output
        assert "Last edit to /test/file.txt undone successfully" in result.output
        mock_write_text.assert_called_with("Line 1\nLine 2")

    # Test attempting to undo when there's no history
    edit_tool._file_history.clear()
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ):
        with pytest.raises(ToolError, match="No edit history found"):
            await edit_tool(command="undo_edit", path="/test/file.txt")


@pytest.mark.asyncio
async def test_validate_path():
    edit_tool = EditTool()

    # Test with valid absolute paths
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=False
    ):
        edit_tool.validate_path("view", Path("/valid/path.txt"))

    # Test with relative paths (should raise an error)
    with pytest.raises(ToolError, match="not an absolute path"):
        edit_tool.validate_path("view", Path("relative/path.txt"))

    # Test with non-existent paths for non-create commands (should raise an error)
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ToolError, match="does not exist"):
            edit_tool.validate_path("view", Path("/nonexistent/file.txt"))

    # Test with existing paths for create command (should raise an error)
    with patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(ToolError, match="File already exists"):
            edit_tool.validate_path("create", Path("/existing/file.txt"))

    # Test with directory paths for non-view commands (should raise an error)
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ):
        with pytest.raises(ToolError, match="is a directory"):
            edit_tool.validate_path("str_replace", Path("/directory/path"))

    # Test with directory path for view command (should not raise an error)
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ):
        edit_tool.validate_path("view", Path("/directory/path"))
