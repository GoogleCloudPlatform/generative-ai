from typing import Callable

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.data_model.tasks import (
    EnvAssertion,
    EnvFunctionCall,
    InitializationData,
)
from tau2.environment.environment import Environment
from tau2.environment.tool import Tool
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


@pytest.fixture
def domain_name() -> str:
    return "mock_domain"


@pytest.fixture
def policy() -> str:
    return "You are a helpful assistant."


@pytest.fixture
def mock_toolkit_class() -> Callable[[], ToolKitBase]:
    class MockToolkit(ToolKitBase):
        def __init__(self):
            self.val = 0

        @is_tool(ToolType.READ)
        def tool1(self, param1: int) -> str:
            self.val += param1
            return str(self.val)

        @is_tool(ToolType.READ)
        def tool2(self, param2: int) -> str:
            self.val += param2
            return str(self.val)

    return MockToolkit


@pytest.fixture
def mock_user_toolkit_class() -> Callable[[], ToolKitBase]:
    class MockUserToolkit(ToolKitBase):
        def __init__(self):
            self.val = 0

        @is_tool(ToolType.READ)
        def tool1(self, param1: int) -> str:
            self.val += param1
            return str(self.val)

        @is_tool(ToolType.READ)
        def tool4(self, param4: int) -> str:
            self.val += param4
            return str(self.val)

    return MockUserToolkit


@pytest.fixture
def super_mock_toolkit_class(
    mock_toolkit_class: Callable[[], ToolKitBase],
) -> Callable[[], ToolKitBase]:
    class SuperMockToolkit(mock_toolkit_class):
        @is_tool(ToolType.READ)
        def tool3(self, param3: int) -> str:
            self.val += param3
            return str(self.val)

    return SuperMockToolkit


@pytest.fixture
def message_history() -> list[Message]:
    return [
        UserMessage(
            id="1",
            content="Create a task called 'Important Meeting' for user_1",
            role="user",
        ),
        AssistantMessage(
            id="2",
            content=None,
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="3",
                    name="create_task",
                    arguments={"user_id": "user_1", "title": "Important Meeting"},
                )
            ],
        ),
        ToolMessage(
            id="3",
            content='{"task_id": "task_2", "title": "Important Meeting", "description": null, "status": "pending"}',
            role="tool",
        ),
        AssistantMessage(
            id="4",
            content="Ok, I've created the task for you. The task ID is task_2.",
            role="assistant",
        ),
        UserMessage(id="5", content="Please mark task_1 as completed", role="user"),
        AssistantMessage(
            id="6",
            content=None,
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="6",
                    name="update_task_status",
                    arguments={"task_id": "task_1", "status": "completed"},
                )
            ],
        ),
        ToolMessage(
            id="6",
            content='{"task_id": "task_1", "title": "Test task", "description": "A test task", "status": "completed"}',
            role="tool",
        ),
        AssistantMessage(
            id="7", content="I've marked task_1 as completed.", role="assistant"
        ),
    ]


@pytest.fixture
def message_history_with_user_tool() -> list[Message]:
    return [
        UserMessage(
            id="1",
            role="user",
            tool_calls=[
                ToolCall(
                    id="1",
                    name="tool1",
                    arguments={"param1": 1},
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="1",
            content="1",
            role="tool",
            requestor="user",
        ),
        UserMessage(
            id="2",
            role="user",
            tool_calls=[
                ToolCall(
                    id="2",
                    name="tool4",
                    arguments={"param4": 4},
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="2",
            content="5",
            role="tool",
            requestor="user",
        ),
        UserMessage(
            id="3",
            role="user",
            content="what's the value of val?",
        ),
        AssistantMessage(
            id="4",
            role="assistant",
            content="The value of val is 5.",
        ),
    ]


@pytest.fixture
def initialization_data() -> InitializationData:
    return InitializationData(
        agent_data={
            "tasks": {
                "task_1": {"status": "completed"},
                "task_2": {
                    "task_id": "task_2",
                    "title": "Important Meeting",
                    "description": None,
                    "status": "pending",
                },
            },
            "users": {
                "user_1": {
                    "tasks": ["task_1", "task_2"],
                }
            },
        }
    )


@pytest.fixture
def initialization_actions() -> list[EnvFunctionCall]:
    return [
        EnvFunctionCall(
            env_type="assistant",
            func_name="create_task",
            arguments={"user_id": "user_1", "title": "Important Meeting"},
        ),
        EnvFunctionCall(
            env_type="assistant",
            func_name="update_task_status",
            arguments={"task_id": "task_1", "status": "completed"},
        ),
    ]


def test_toolkit(
    mock_toolkit_class: Callable[[], ToolKitBase],
    super_mock_toolkit_class: Callable[[], ToolKitBase],
    mock_user_toolkit_class: Callable[[], ToolKitBase],
):
    # Test MockToolkit
    mock_toolkit = mock_toolkit_class()
    assert len(mock_toolkit.tools) == 2
    assert mock_toolkit.tools.keys() == {"tool1", "tool2"}
    assert mock_toolkit.get_tools().keys() == {"tool1", "tool2"}
    assert all(isinstance(tool, Tool) for tool in mock_toolkit.get_tools().values())
    assert mock_toolkit.use_tool("tool1", param1=1) == "1"
    assert mock_toolkit.use_tool("tool2", param2=2) == "3"

    # Test SuperMockToolkit
    super_mock_toolkit = super_mock_toolkit_class()
    assert len(super_mock_toolkit.tools) == 3
    assert super_mock_toolkit.tools.keys() == {"tool1", "tool2", "tool3"}
    assert super_mock_toolkit.use_tool("tool1", param1=1) == "1"
    assert super_mock_toolkit.use_tool("tool2", param2=2) == "3"
    assert super_mock_toolkit.use_tool("tool3", param3=3) == "6"

    # Test MockUserToolkit
    mock_user_toolkit = mock_user_toolkit_class()
    assert len(mock_user_toolkit.tools) == 2
    assert mock_user_toolkit.tools.keys() == {"tool1", "tool4"}
    assert mock_user_toolkit.use_tool("tool1", param1=1) == "1"
    assert mock_user_toolkit.use_tool("tool4", param4=4) == "5"


def test_environment(
    mock_toolkit_class: Callable[[], ToolKitBase],
    domain_name: str,
    policy: str,
):
    toolkit = mock_toolkit_class()
    environment = Environment(domain_name=domain_name, policy=policy, tools=toolkit)
    assert environment.get_policy() == policy
    assert environment.use_tool("tool1", param1=1) == "1"
    response = environment.get_response(
        ToolCall(id="1", name="tool2", arguments={"param2": 2})
    )
    assert isinstance(response, ToolMessage)
    assert response.id == "1"
    assert response.content == "3"
    assert response.role == "tool"


def test_environment_with_user_tool(
    mock_toolkit_class: Callable[[], ToolKitBase],
    mock_user_toolkit_class: Callable[[], ToolKitBase],
    message_history_with_user_tool: list[Message],
):
    environment = Environment(
        domain_name="mock_domain",
        policy="You are a helpful assistant.",
        tools=mock_toolkit_class(),
        user_tools=mock_user_toolkit_class(),
    )
    environment.set_state(
        initialization_data=None,
        initialization_actions=None,
        message_history=message_history_with_user_tool,
    )
    response = environment.get_response(
        ToolCall(
            id="1",
            name="tool1",
            arguments={"param1": 1},
            requestor="user",
        )
    )
    assert isinstance(response, ToolMessage)
    assert response.id == "1"
    assert response.content == "6"
    assert response.role == "tool"
    assert response.requestor == "user"

    # Assistant tool call, independent of user tool call
    response = environment.get_response(
        ToolCall(
            id="2",
            name="tool2",
            arguments={"param2": 2},
            requestor="assistant",
        )
    )
    assert isinstance(response, ToolMessage)
    assert response.id == "2"
    assert response.content == "2"
    assert response.role == "tool"
    assert response.requestor == "assistant"

    # tool4 should not be found for assistant
    response = environment.get_response(
        ToolCall(
            id="3",
            name="tool4",
            arguments={"param4": 4},
            requestor="assistant",
        )
    )
    assert isinstance(response, ToolMessage)
    assert response.error is True
    assert response.content == "Error: Tool 'tool4' not found."


def test_environment_set_state_message_history(
    get_environment: Callable[[], Environment], message_history: list[Message]
):
    environment = get_environment()
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    environment.set_state(
        initialization_data=None,
        initialization_actions=None,
        message_history=message_history,
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "completed"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )


def test_environment_set_state_initialization_data(
    get_environment: Callable[[], Environment], initialization_data: InitializationData
):
    environment = get_environment()
    print(environment.tools.db.model_dump_json(indent=2))
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    environment.set_state(
        initialization_data=initialization_data,
        initialization_actions=None,
        message_history=[],
    )
    print(environment.tools.db.model_dump_json(indent=2))
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "completed"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )


def test_environment_set_state_initialization_actions(
    get_environment: Callable[[], Environment],
    initialization_actions: list[EnvFunctionCall],
):
    environment = get_environment()
    print(environment.tools.db.model_dump_json(indent=2))
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    environment.set_state(
        initialization_data=None,
        initialization_actions=initialization_actions,
        message_history=[],
    )
    print(environment.tools.db.model_dump_json(indent=2))
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "completed"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )
