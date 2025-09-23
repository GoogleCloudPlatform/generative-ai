import json

import pytest

from tau2.run import get_tasks
from tau2.utils import DATA_DIR
from tau2.utils.utils import get_dict_hash, show_dict_diff


@pytest.fixture
def base_task_name() -> str:
    return "create_task_1"


@pytest.fixture
def task_with_initial_state_message_history_name() -> str:
    return "update_task_with_message_history"


@pytest.fixture
def task_with_initial_state_initialization_data_name():
    return "update_task_with_initialization_data"


@pytest.fixture
def tasks_dict():
    task_file = DATA_DIR / "tau2" / "domains" / "mock" / "tasks.json"
    with open(task_file, "r") as f:
        task_dicts = json.load(f)
    tasks_dict = {v["id"]: v for v in task_dicts}
    return tasks_dict


def test_get_task_base(base_task_name: str, tasks_dict: dict):
    task_dict = tasks_dict[base_task_name]
    task_instance = get_tasks("mock", task_ids=[base_task_name])[0]
    task_instance_dict = task_instance.model_dump(
        exclude_unset=True, exclude_defaults=True, exclude_none=True
    )
    print(show_dict_diff(task_dict, task_instance_dict))
    assert get_dict_hash(task_dict) == get_dict_hash(task_instance_dict)


def test_get_task_with_initial_state_message_history(
    task_with_initial_state_message_history_name: str, tasks_dict: dict
):
    task_dict = tasks_dict[task_with_initial_state_message_history_name]
    task_instance = get_tasks(
        "mock", task_ids=[task_with_initial_state_message_history_name]
    )[0]
    task_instance_dict = task_instance.model_dump(
        exclude_unset=True, exclude_defaults=True, exclude_none=True
    )
    # FIXME: `ticket: null` is not removed in task_dict, but excluded in task_instance_dict
    print(json.dumps(task_dict, indent=2))
    print(json.dumps(task_instance_dict, indent=2))
    print(show_dict_diff(task_dict, task_instance_dict))
    assert get_dict_hash(task_dict) == get_dict_hash(task_instance_dict)


def test_get_task_with_initial_state_initialization_data(
    task_with_initial_state_initialization_data_name: str, tasks_dict: dict
):
    task_dict = tasks_dict[task_with_initial_state_initialization_data_name]
    task_instance = get_tasks(
        "mock", task_ids=[task_with_initial_state_initialization_data_name]
    )[0]
    task_instance_dict = task_instance.model_dump(
        exclude_unset=True, exclude_defaults=True, exclude_none=True
    )
    print(json.dumps(task_dict, indent=2))
    print(json.dumps(task_instance_dict, indent=2))
    print(show_dict_diff(task_dict, task_instance_dict))
    assert get_dict_hash(task_dict) == get_dict_hash(task_instance_dict)
