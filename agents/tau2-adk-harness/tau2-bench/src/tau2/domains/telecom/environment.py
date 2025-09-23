# Copyright Sierra
from functools import partial
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.telecom.data_model import LineStatus, TelecomDB
from tau2.domains.telecom.tools import TelecomTools
from tau2.domains.telecom.user_data_model import PaymentRequest, TelecomUserDB
from tau2.domains.telecom.user_tools import TelecomUserTools
from tau2.domains.telecom.utils import (
    TELECOM_DB_PATH,
    TELECOM_MAIN_POLICY_PATH,
    TELECOM_MAIN_POLICY_SOLO_PATH,
    TELECOM_TASK_SET_PATH,
    TELECOM_TASK_SET_PATH_FULL,
    TELECOM_TASK_SET_PATH_SMALL,
    TELECOM_TECH_SUPPORT_POLICY_MANUAL_PATH,
    TELECOM_TECH_SUPPORT_POLICY_MANUAL_SOLO_PATH,
    TELECOM_TECH_SUPPORT_POLICY_WORKFLOW_PATH,
    TELECOM_TECH_SUPPORT_POLICY_WORKFLOW_SOLO_PATH,
    TELECOM_USER_DB_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


class TelecomEnvironment(Environment):
    tools: TelecomTools
    user_tools: TelecomUserTools

    def __init__(
        self,
        domain_name: str,
        policy: str,
        tools: TelecomTools,
        user_tools: TelecomUserTools,
    ):
        super().__init__(domain_name, policy, tools, user_tools)

    def sync_tools(self):
        """
        Sync the tools with the user's surroundings.
        If the line is roaming enabled, then the user is allowed to roam.
        """
        if self.user_tools.db.surroundings.phone_number is None:
            return
        phone_number = self.user_tools.db.surroundings.phone_number
        line = self.tools._get_line_by_phone(phone_number)
        if line is None:
            raise ValueError(
                f"Wrong scenario, line not found for phone number: {phone_number}"
            )
        # Check if the line is active
        if line.status == LineStatus.ACTIVE:
            self.user_tools.db.surroundings.line_active = True
        else:
            self.user_tools.db.surroundings.line_active = False

        # Check if the line is roaming enabled
        if line.roaming_enabled:
            self.user_tools.db.surroundings.roaming_allowed = True
        else:
            self.user_tools.db.surroundings.roaming_allowed = False

        # Check if the user has exceeded their data usage limit
        plan = self.tools._get_plan_by_id(line.plan_id)
        if plan is None:
            raise ValueError(
                f"Wrong scenario, invalid plan id ({line.plan_id}) for the phone number {phone_number}"
            )
        if line.data_used_gb >= plan.data_limit_gb + line.data_refueling_gb:
            self.user_tools.db.surroundings.mobile_data_usage_exceeded = True
        else:
            self.user_tools.db.surroundings.mobile_data_usage_exceeded = False

        # Check if the user has paid a bill
        current_payment_request = self.user_tools.db.surroundings.payment_request
        if current_payment_request is not None:
            if current_payment_request.paid:
                self.tools._set_bill_to_paid(current_payment_request.bill_id)
                self.user_tools.db.surroundings.payment_request = None

        # Check if the user has a payment request
        current_payment_request = self.user_tools.db.surroundings.payment_request
        if (
            current_payment_request is None
        ):  # If there already is a payment request, do nothing
            customer = self.tools.get_customer_by_phone(phone_number)
            bills = self.tools._get_bills_awaiting_payment(customer)
            if len(bills) != 0:
                bill = bills[0]
                self.user_tools.db.surroundings.payment_request = PaymentRequest(
                    bill_id=bill.bill_id, amount_due=bill.total_due
                )


def get_environment(
    db: Optional[TelecomDB] = None,
    user_db: Optional[TelecomUserDB] = None,
    solo_mode: bool = False,
    policy_type: str = "manual",  # "manual" or "workflow"
) -> TelecomEnvironment:
    if db is None:
        db = TelecomDB.load(TELECOM_DB_PATH)
    tools = TelecomTools(db)
    if user_db is None:
        user_db = TelecomUserDB.load(TELECOM_USER_DB_PATH)
    user_tools = TelecomUserTools(user_db)
    if not solo_mode:
        policy_path = TELECOM_MAIN_POLICY_PATH
        if policy_type == "manual":
            tech_support_policy_path = TELECOM_TECH_SUPPORT_POLICY_MANUAL_PATH
        elif policy_type == "workflow":
            tech_support_policy_path = TELECOM_TECH_SUPPORT_POLICY_WORKFLOW_PATH
        else:
            raise ValueError(f"Invalid policy type: {policy_type}")
    else:
        policy_path = TELECOM_MAIN_POLICY_SOLO_PATH
        if policy_type == "manual":
            tech_support_policy_path = TELECOM_TECH_SUPPORT_POLICY_MANUAL_SOLO_PATH
        elif policy_type == "workflow":
            tech_support_policy_path = TELECOM_TECH_SUPPORT_POLICY_WORKFLOW_SOLO_PATH
        else:
            raise ValueError(f"Invalid policy type: {policy_type}")
    main_policy = load_file(policy_path)
    tech_support_policy = load_file(tech_support_policy_path)
    policy = (
        "<main_policy>\n"
        + main_policy
        + "\n</main_policy>\n"
        + "<tech_support_policy>\n"
        + tech_support_policy
        + "\n</tech_support_policy>"
    )
    if policy_type == "manual":
        domain_name = "telecom"
    else:
        domain_name = "telecom-workflow"
    env = TelecomEnvironment(
        domain_name=domain_name,
        policy=policy,
        tools=tools,
        user_tools=user_tools,
    )
    if solo_mode:
        env.set_solo_mode(True)
    return env


get_environment_manual_policy = partial(get_environment, policy_type="manual")
get_environment_workflow_policy = partial(get_environment, policy_type="workflow")


def load_tasks(path: str) -> list[Task]:
    """Load tasks from a data file, could be json, yaml or toml file."""
    tasks = load_file(path)
    if isinstance(tasks, dict) and "tasks" in tasks:
        tasks = tasks["tasks"]
    return [Task.model_validate(task) for task in tasks]


def get_tasks_full() -> list[Task]:
    return load_tasks(TELECOM_TASK_SET_PATH_FULL)


def get_tasks_small() -> list[Task]:
    return load_tasks(TELECOM_TASK_SET_PATH_SMALL)


def get_tasks() -> list[Task]:
    return load_tasks(TELECOM_TASK_SET_PATH)


if __name__ == "__main__":
    env = get_environment()
    # print(env.get_tools())
    for tool in env.get_user_tools():
        print(tool.name)
