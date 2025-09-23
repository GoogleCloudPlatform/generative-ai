import json
from copy import deepcopy

import pytest

from tau2.config import (
    DEFAULT_LLM_AGENT,
    DEFAULT_LLM_ARGS_AGENT,
    DEFAULT_LLM_ARGS_USER,
    DEFAULT_LLM_USER,
)
from tau2.data_model.simulation import RunConfig
from tau2.data_model.tasks import EnvAssertion, RewardType, Task, make_task
from tau2.run import (
    EvaluationType,
    get_options,
    get_tasks,
    load_tasks,
    run_domain,
    run_task,
    run_tasks,
)


@pytest.fixture
def run_config() -> RunConfig:
    """Test that we can get available options from the registry"""
    return RunConfig(
        domain="mock",
        agent="llm_agent",
        user="user_simulator",
        task_ids=["create_task_1"],
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        num_trials=3,
        max_steps=20,
        max_errors=10,
        save_to=None,
        llm_review=False,
        max_concurrency=3,
    )


@pytest.fixture
def run_config_solo() -> RunConfig:
    return RunConfig(
        domain="mock",
        agent="llm_solo_agent",
        user="dummy_user",
        task_ids=["create_task_1"],
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        num_trials=3,
        max_steps=20,
        max_errors=10,
        save_to=None,
        llm_review=False,
        max_concurrency=3,
    )


def test_get_options():
    """Test that we can get available options from the registry"""
    options = get_options()
    assert options.domains is not None


def test_load_tasks():
    """Test that we can load tasks from the domain"""
    tasks = load_tasks("mock")
    assert len(tasks) > 0


def test_get_tasks():
    """Test that we can load tasks from the domain by id"""
    tasks = get_tasks("mock", task_ids=["create_task_1"])
    assert len(tasks) == 1
    assert tasks[0].id == "create_task_1"


def test_simplified_run(domain_name: str):
    """Test that we can run a task with the mock domain"""

    def run_simple_task(user_instruction: str, domain_name: str):
        task = make_task(
            user_instructions=user_instruction,
            eval_criteria=None,
            initialization_data=None,
            message_history=None,
        )
        simulation = run_tasks(
            domain=domain_name,
            tasks=[task],
            agent="llm_agent",
            user="user_simulator",
            llm_agent=DEFAULT_LLM_AGENT,
            llm_args_agent=deepcopy(DEFAULT_LLM_ARGS_AGENT),
            llm_user=DEFAULT_LLM_USER,
            llm_args_user=deepcopy(DEFAULT_LLM_ARGS_USER),
            max_steps=5,
            max_errors=5,
            evaluation_type=EvaluationType.ENV,
            console_display=False,
            max_concurrency=1,
        )
        return simulation

    simulation = run_simple_task(
        user_instruction="create a task called 'test' for user_1",
        domain_name=domain_name,
    )
    assert simulation is not None


def test_run_tasks_base(domain_name: str, base_task: Task):
    """Test running a task with the mock domain"""
    results = run_tasks(
        domain=domain_name,
        tasks=[base_task],
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        max_concurrency=1,
    )
    # Check that simulation ran and has expected structure
    assert len(results.simulations) == 1
    simulation = results.simulations[0]
    assert simulation.messages is not None
    assert len(simulation.messages) > 0
    assert simulation.start_time is not None
    assert simulation.end_time is not None
    assert simulation.reward_info.reward is not None


def test_run_task_base(domain_name: str, base_task: Task):
    """Test running a task with the mock domain"""
    simulation = run_task(
        domain=domain_name,
        task=base_task,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        evaluation_type=EvaluationType.ENV,
    )
    # Check that simulation ran and has expected structure
    assert simulation.messages is not None
    assert len(simulation.messages) > 0
    assert simulation.start_time is not None
    assert simulation.end_time is not None
    assert simulation.reward_info.reward is not None


def test_run_tasks_message_history(domain_name: str, task_with_message_history: Task):
    """Test running a task with message history"""
    print(task_with_message_history.model_dump_json(indent=2))
    simulation = run_task(
        domain=domain_name,
        task=task_with_message_history,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation is not None


def test_run_tasks_initialization_data(
    domain_name: str, task_with_initialization_data: Task
):
    """Test running a task with initialization data"""
    simulation = run_task(
        domain=domain_name,
        task=task_with_initialization_data,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation is not None


def test_run_tasks_initialization_actions(
    domain_name: str, task_with_initialization_actions: Task
):
    """Test running a task with initialization actions"""
    simulation = run_task(
        domain=domain_name,
        task=task_with_initialization_actions,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation is not None


def test_run_tasks_env_assertions(domain_name: str, task_with_env_assertions: Task):
    """Test running a task with env assertions"""
    simulation = run_task(
        domain=domain_name,
        task=task_with_env_assertions,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        evaluation_type=EvaluationType.ENV,
    )
    # Check that simulation ran and has expected structure
    assert simulation.messages is not None
    assert len(simulation.messages) > 0
    assert simulation.start_time is not None
    assert simulation.end_time is not None
    # These assertions can fail if model is not good enough
    assert simulation.reward_info.reward == 1.0
    assert len(simulation.reward_info.env_assertions) == 1
    assert simulation.reward_info.env_assertions[0].met is True
    # Add an env_assertion that will fail and test that the reward is 0.0
    task_with_env_assertions.evaluation_criteria.env_assertions.append(
        EnvAssertion(
            env_type="assistant",
            func_name="assert_task_status",
            arguments={"task_id": "task_1", "expected_status": "made_up_status"},
        )
    )
    simulation = run_task(
        domain=domain_name,
        task=task_with_env_assertions,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        evaluation_type=EvaluationType.ENV,
    )
    assert simulation.reward_info.reward == 0.0
    assert len(simulation.reward_info.env_assertions) == 2
    assert simulation.reward_info.env_assertions[0].met is True
    assert simulation.reward_info.env_assertions[1].met is False


def test_run_tasks_history_and_env_assertions(
    domain_name: str, task_with_history_and_env_assertions: Task
):
    """Test running a task with history and env assertions"""
    simulation = run_task(
        domain=domain_name,
        task=task_with_history_and_env_assertions,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation is not None


def test_run_tasks_nl_assertions(domain_name: str):
    """Test running a task with the mock domain"""
    task = get_tasks(domain_name, task_ids=["create_task_1_nl_eval"])[0]
    simulation = run_task(
        domain=domain_name,
        task=task,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        evaluation_type=EvaluationType.NL_ASSERTIONS,
    )
    # Check that simulation ran and has expected structure
    assert simulation.messages is not None
    assert len(simulation.messages) > 0
    assert simulation.start_time is not None
    assert simulation.end_time is not None
    assert simulation.reward_info.reward == 1.0
    assert len(simulation.reward_info.nl_assertions) == 2
    assert simulation.reward_info.nl_assertions[0].met is True
    assert simulation.reward_info.nl_assertions[1].met is True

    # Add an nl_assertion that will fail and test that the reward is 0.0
    task.evaluation_criteria.nl_assertions.append("The user is not complimented")
    simulation = run_task(
        domain=domain_name,
        task=task,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
        evaluation_type=EvaluationType.NL_ASSERTIONS,
    )
    assert simulation.reward_info.reward == 0.0

    assert len(simulation.reward_info.nl_assertions) == 3
    assert simulation.reward_info.nl_assertions[0].met is True
    assert simulation.reward_info.nl_assertions[1].met is True
    assert simulation.reward_info.nl_assertions[2].met is False


def test_run_tasks_action_checks(domain_name: str, task_with_action_checks: Task):
    """Test running a task with action checks"""
    simulation = run_task(
        domain=domain_name,
        task=task_with_action_checks,
        agent="llm_agent",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation is not None
    # Following assertions can fail if model is not good enough
    assert simulation.reward_info.reward == 1.0
    assert simulation.reward_info.reward_breakdown[RewardType.DB] == 1.0
    assert simulation.reward_info.reward_breakdown[RewardType.ACTION] == 1.0


def test_run_domain(run_config: RunConfig):
    """Test running a domain with the mock domain
    Requires environment manager to be running
    """
    simulation_results = run_domain(run_config)
    assert simulation_results is not None


def test_run_gt_agent(domain_name: str, base_task: Task):
    """Test running gt agent"""
    simulation_results = run_tasks(
        domain=domain_name,
        tasks=[base_task],
        agent="llm_agent_gt",
        user="user_simulator",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation_results is not None


def test_run_solo_agent(domain_name: str, base_task: Task):
    """Test running solo agent"""
    simulation_results = run_tasks(
        domain=domain_name,
        tasks=[base_task],
        agent="llm_agent_solo",
        user="dummy_user",
        llm_agent="gpt-3.5-turbo",
        llm_args_agent={},
        llm_user="gpt-3.5-turbo",
        llm_args_user={},
    )
    assert simulation_results is not None
