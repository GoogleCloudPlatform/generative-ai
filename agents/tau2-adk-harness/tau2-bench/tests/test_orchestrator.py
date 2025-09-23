from copy import deepcopy
from typing import Callable

import pytest

from tau2.agent.llm_agent import LLMAgent, LLMSoloAgent
from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.data_model.tasks import EnvAssertion, InitialState, Task
from tau2.environment.environment import Environment
from tau2.orchestrator.orchestrator import (
    DEFAULT_FIRST_AGENT_MESSAGE,
    Orchestrator,
    Role,
)
from tau2.user.user_simulator import DummyUser, UserSimulator


@pytest.fixture
def user_simulator() -> UserSimulator:
    return UserSimulator(
        instructions="You are a user simulator.",
        llm="gpt-3.5-turbo",
        llm_args={"temperature": 0.0},
    )


@pytest.fixture
def dummy_user() -> DummyUser:
    return DummyUser(
        instructions="You are a dummy user.",
        llm="gpt-3.5-turbo",
        llm_args={"temperature": 0.0},
    )


@pytest.fixture
def agent(get_environment: Callable[[], Environment]) -> LLMAgent:
    environment = get_environment()
    return LLMAgent(
        tools=environment.get_tools(),
        domain_policy=environment.get_policy(),
        llm="gpt-3.5-turbo",
        llm_args={"temperature": 0.0},
    )


@pytest.fixture
def solo_agent(
    get_environment: Callable[[], Environment], base_task: Task
) -> LLMSoloAgent:
    environment = get_environment()
    return LLMSoloAgent(
        tools=environment.get_tools(),
        domain_policy=environment.get_policy(),
        task=base_task,
        llm="gpt-3.5-turbo",
        llm_args={"temperature": 0.0},
    )


def test_orchestrator_initialize_base(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    get_environment: Callable[[], Environment],
    base_task: Task,
):
    orchestrator = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=base_task,
    )
    orchestrator.initialize()

    # Check Initialization
    assert orchestrator.from_role == Role.AGENT
    assert orchestrator.to_role == Role.USER
    assert orchestrator.step_count == 0
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.trajectory) == 1
    assert isinstance(orchestrator.trajectory[0], AssistantMessage)
    assert orchestrator.trajectory[0].content == DEFAULT_FIRST_AGENT_MESSAGE.content
    assert orchestrator.message.content == DEFAULT_FIRST_AGENT_MESSAGE.content


def test_orchestrator_initialize_with_message_history(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    get_environment: Callable[[], Environment],
    task_with_message_history: Task,
):
    orchestrator = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=task_with_message_history,
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    orchestrator.initialize()
    assert orchestrator.from_role == Role.AGENT
    assert orchestrator.to_role == Role.USER
    assert orchestrator.step_count == 0
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.get_trajectory()) == len(
        task_with_message_history.initial_state.message_history
    )

    user_state = orchestrator.user_state
    print(user_state.model_dump_json(indent=2))
    assert len(user_state.messages) == 1

    agent_state = orchestrator.agent_state
    print(agent_state.model_dump_json(indent=2))
    assert len(agent_state.messages) == len(
        task_with_message_history.initial_state.message_history
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )


def test_orchestrator_initialize_with_initialization_data(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    get_environment: Callable[[], Environment],
    task_with_initialization_data: Task,
):
    orchestrator = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=task_with_initialization_data,
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    orchestrator.initialize()
    print(orchestrator.environment.tools.db.model_dump_json(indent=2))
    assert orchestrator.from_role == Role.AGENT
    assert orchestrator.to_role == Role.USER
    assert orchestrator.step_count == 0
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.get_trajectory()) == 1
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )


def test_orchestrator_initialize_with_initialization_actions(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    get_environment: Callable[[], Environment],
    task_with_initialization_actions: Task,
):
    orchestrator = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=task_with_initialization_actions,
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 1},
        )
    )
    orchestrator.initialize()
    print(orchestrator.environment.tools.db.model_dump_json(indent=2))
    assert orchestrator.from_role == Role.AGENT
    assert orchestrator.to_role == Role.USER
    assert orchestrator.step_count == 0
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.get_trajectory()) == 1
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_number_of_tasks",
            arguments={"user_id": "user_1", "expected_number": 2},
        )
    )


def test_orchestrator_step(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    base_task: Task,
    get_environment: Callable[[], Environment],
):
    orchestrator = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=base_task,
    )
    orchestrator.initialize()

    # Check Step 1
    orchestrator.step()
    assert orchestrator.from_role == Role.USER
    assert orchestrator.to_role == Role.AGENT
    assert orchestrator.step_count == 1
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.get_trajectory()) == 2
    assert isinstance(orchestrator.get_trajectory()[1], UserMessage)
    assert isinstance(orchestrator.message, UserMessage)

    # Check Step 2
    orchestrator.step()
    assert orchestrator.from_role == Role.AGENT
    assert orchestrator.to_role in [Role.ENV, Role.USER]
    assert orchestrator.step_count == 2
    assert not orchestrator.done
    assert orchestrator.termination_reason is None
    assert len(orchestrator.get_trajectory()) == 3
    assert isinstance(orchestrator.get_trajectory()[2], AssistantMessage)
    assert isinstance(orchestrator.message, AssistantMessage)


def test_orchestrator_restart(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    base_task: Task,
    get_environment: Callable[[], Environment],
):
    orchestrator1 = Orchestrator(
        domain=domain_name,
        user=user_simulator,
        agent=agent,
        environment=get_environment(),
        task=base_task,
        seed=300,
    )
    orchestrator1.initialize()
    # Create a partial message history
    for _ in range(3):
        orchestrator1.step()
    partial_message_history = orchestrator1.get_trajectory()

    # Create a new task with the partial message history
    task2 = deepcopy(base_task)
    initial_state = InitialState(
        message_history=partial_message_history,
        variables={},
        state={},
    )
    task2.initial_state = initial_state
    # Create a new orchestrator with the partial new task
    orchestrator2 = Orchestrator(
        domain=domain_name,
        environment=get_environment(),
        user=user_simulator,
        agent=agent,
        task=task2,
        seed=300,
    )
    orchestrator2.initialize()

    assert orchestrator1.to_role == orchestrator2.to_role
    assert orchestrator1.from_role == orchestrator2.from_role
    assert orchestrator1.message.content == orchestrator2.message.content
    for msg1, msg2 in zip(
        orchestrator1.get_trajectory(), orchestrator2.get_trajectory()
    ):
        assert msg1.content == msg2.content

    ## Step each orchestrator 3 times
    for _ in range(3):
        orchestrator1.step()
        orchestrator2.step()
        print("--------------------------------")
        print("Orchestrator 1")
        print(orchestrator1.message)
        print("--------------------------------")
        print("Orchestrator 2")
        print(orchestrator2.message)
        print("--------------------------------")


def test_orchestrator_run(
    domain_name: str,
    user_simulator: UserSimulator,
    agent: LLMAgent,
    base_task: Task,
    get_environment: Callable[[], Environment],
):
    orchestrator = Orchestrator(
        domain=domain_name,
        environment=get_environment(),
        user=user_simulator,
        agent=agent,
        task=base_task,
        max_steps=10,
    )
    simulation_run = orchestrator.run()
    assert simulation_run is not None


def test_orchestrator_run_with_solo_agent(
    domain_name: str,
    dummy_user: DummyUser,
    solo_agent: LLMSoloAgent,
    base_task: Task,
    get_environment: Callable[[], Environment],
):
    orchestrator = Orchestrator(
        domain=domain_name,
        environment=get_environment(solo_mode=True),
        user=dummy_user,
        agent=solo_agent,
        task=base_task,
        max_steps=10,
        solo_mode=True,
    )
    simulation_run = orchestrator.run()
    assert simulation_run is not None

    orchestrator.environment.run_env_assertion(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_2", "expected_status": "pending"},
        )
    )
