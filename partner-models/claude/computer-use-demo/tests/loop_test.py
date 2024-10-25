from unittest import mock

from anthropic.types import TextBlock, ToolUseBlock
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaTextBlockParam

from computer_use_demo.loop import APIProvider, sampling_loop


async def test_loop():
    client = mock.Mock()
    client.beta.messages.with_raw_response.create.return_value = mock.Mock()
    client.beta.messages.with_raw_response.create.return_value.parse.side_effect = [
        mock.Mock(
            spec=BetaMessage,
            content=[
                TextBlock(type="text", text="Hello"),
                ToolUseBlock(
                    type="tool_use", id="1", name="computer", input={"action": "test"}
                ),
            ],
        ),
        mock.Mock(spec=BetaMessage, content=[TextBlock(type="text", text="Done!")]),
    ]

    tool_collection = mock.AsyncMock()
    tool_collection.run.return_value = mock.Mock(
        output="Tool output", error=None, base64_image=None
    )

    output_callback = mock.Mock()
    tool_output_callback = mock.Mock()
    api_response_callback = mock.Mock()

    with mock.patch(
        "computer_use_demo.loop.Anthropic", return_value=client
    ), mock.patch(
        "computer_use_demo.loop.ToolCollection", return_value=tool_collection
    ):
        messages: list[BetaMessageParam] = [{"role": "user", "content": "Test message"}]
        result = await sampling_loop(
            model="test-model",
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix="",
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            api_key="test-key",
        )

        assert len(result) == 4
        assert result[0] == {"role": "user", "content": "Test message"}
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"
        assert result[3]["role"] == "assistant"

        assert client.beta.messages.with_raw_response.create.call_count == 2
        tool_collection.run.assert_called_once_with(
            name="computer", tool_input={"action": "test"}
        )
        output_callback.assert_called_with(
            BetaTextBlockParam(text="Done!", type="text")
        )
        assert output_callback.call_count == 3
        assert tool_output_callback.call_count == 1
        assert api_response_callback.call_count == 2
