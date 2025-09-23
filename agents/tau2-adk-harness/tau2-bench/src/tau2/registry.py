import json
from typing import Callable, Dict, Optional, Type

from loguru import logger
from pydantic import BaseModel

from tau2.agent.base import BaseAgent
from tau2.agent.llm_agent import LLMAgent, LLMGTAgent, LLMSoloAgent
from tau2.data_model.tasks import Task
from tau2.domains.airline.environment import \
    get_environment as airline_domain_get_environment
from tau2.domains.airline.environment import \
    get_tasks as airline_domain_get_tasks
from tau2.domains.mock.environment import \
    get_environment as mock_domain_get_environment
from tau2.domains.mock.environment import get_tasks as mock_domain_get_tasks
from tau2.domains.retail.environment import \
    get_environment as retail_domain_get_environment
from tau2.domains.retail.environment import \
    get_tasks as retail_domain_get_tasks
from tau2.domains.telecom.environment import \
    get_environment_manual_policy as \
    telecom_domain_get_environment_manual_policy
from tau2.domains.telecom.environment import \
    get_environment_workflow_policy as \
    telecom_domain_get_environment_workflow_policy
from tau2.domains.telecom.environment import \
    get_tasks as telecom_domain_get_tasks
from tau2.domains.telecom.environment import \
    get_tasks_full as telecom_domain_get_tasks_full
from tau2.domains.telecom.environment import \
    get_tasks_small as telecom_domain_get_tasks_small
from tau2.environment.environment import Environment
from tau2.user.base import BaseUser
from tau2.user.user_simulator import DummyUser, UserSimulator


class RegistryInfo(BaseModel):
    """Options for the registry"""

    domains: list[str]
    agents: list[str]
    users: list[str]
    task_sets: list[str]


class Registry:
    """Registry for Users, Agents, and Domains"""

    def __init__(self):
        self._users: Dict[str, Type[BaseUser]] = {}
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._domains: Dict[str, Callable[[], Environment]] = {}
        self._tasks: Dict[str, Callable[[], list[Task]]] = {}

    def register_user(
        self,
        user_constructor: type[BaseUser],
        name: Optional[str] = None,
    ):
        """Decorator to register a new User implementation"""
        try:
            if not issubclass(user_constructor, BaseUser):
                raise TypeError(f"{user_constructor.__name__} must implement UserBase")
            key = name or user_constructor.__name__
            if key in self._users:
                raise ValueError(f"User {key} already registered")
            self._users[key] = user_constructor
        except Exception as e:
            logger.error(f"Error registering user {name}: {str(e)}")
            raise

    def register_agent(
        self,
        agent_constructor: type[BaseAgent],
        name: Optional[str] = None,
    ):
        """Decorator to register a new Agent implementation"""
        if not issubclass(agent_constructor, BaseAgent):
            raise TypeError(f"{agent_constructor.__name__} must implement AgentBase")
        key = name or agent_constructor.__name__
        if key in self._agents:
            raise ValueError(f"Agent {key} already registered")
        self._agents[key] = agent_constructor

    def register_domain(
        self,
        get_environment: Callable[[], Environment],
        name: str,
    ):
        """Register a new Domain implementation"""
        try:
            if name in self._domains:
                raise ValueError(f"Domain {name} already registered")
            self._domains[name] = get_environment
        except Exception as e:
            logger.error(f"Error registering domain {name}: {str(e)}")
            raise

    def register_tasks(
        self,
        get_tasks: Callable[[], list[Task]],
        name: str,
    ):
        """Register a new Domain implementation"""
        try:
            if name in self._tasks:
                raise ValueError(f"Tasks {name} already registered")
            self._tasks[name] = get_tasks
        except Exception as e:
            logger.error(f"Error registering tasks {name}: {str(e)}")
            raise

    def get_user_constructor(self, name: str) -> Type[BaseUser]:
        """Get a registered User implementation by name"""
        if name not in self._users:
            raise KeyError(f"User {name} not found in registry")
        return self._users[name]

    def get_agent_constructor(self, name: str) -> Type[BaseAgent]:
        """Get a registered Agent implementation by name"""
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found in registry")
        return self._agents[name]

    def get_env_constructor(self, name: str) -> Callable[[], Environment]:
        """Get a registered Domain by name"""
        if name not in self._domains:
            raise KeyError(f"Domain {name} not found in registry")
        return self._domains[name]

    def get_tasks_loader(self, name: str) -> Callable[[], list[Task]]:
        """Get a registered Task Set by name"""
        if name not in self._tasks:
            raise KeyError(f"Task Set {name} not found in registry")
        return self._tasks[name]

    def get_users(self) -> list[str]:
        """Get all registered Users"""
        return list(self._users.keys())

    def get_agents(self) -> list[str]:
        """Get all registered Agents"""
        return list(self._agents.keys())

    def get_domains(self) -> list[str]:
        """Get all registered Domains"""
        return list(self._domains.keys())

    def get_task_sets(self) -> list[str]:
        """Get all registered Task Sets"""
        return list(self._tasks.keys())

    def get_info(self) -> RegistryInfo:
        """
        Returns information about the registry.
        """
        try:
            info = RegistryInfo(
                users=self.get_users(),
                agents=self.get_agents(),
                domains=self.get_domains(),
                task_sets=self.get_task_sets(),
            )
            return info
        except Exception as e:
            logger.error(f"Error getting registry info: {str(e)}")
            raise


# Create a global registry instance
try:
    registry = Registry()
    logger.debug("Registering default components...")
    registry.register_user(UserSimulator, "user_simulator")
    registry.register_user(DummyUser, "dummy_user")
    registry.register_agent(LLMAgent, "llm_agent")
    registry.register_agent(LLMGTAgent, "llm_agent_gt")
    registry.register_agent(LLMSoloAgent, "llm_agent_solo")
    registry.register_domain(mock_domain_get_environment, "mock")
    registry.register_tasks(mock_domain_get_tasks, "mock")
    registry.register_domain(airline_domain_get_environment, "airline")
    registry.register_tasks(airline_domain_get_tasks, "airline")
    registry.register_domain(retail_domain_get_environment, "retail")
    registry.register_tasks(retail_domain_get_tasks, "retail")
    registry.register_domain(telecom_domain_get_environment_manual_policy, "telecom")
    registry.register_domain(
        telecom_domain_get_environment_workflow_policy, "telecom-workflow"
    )
    registry.register_tasks(telecom_domain_get_tasks_full, "telecom_full")
    registry.register_tasks(telecom_domain_get_tasks_small, "telecom_small")
    registry.register_tasks(telecom_domain_get_tasks, "telecom")
    registry.register_tasks(telecom_domain_get_tasks, "telecom-workflow")
    logger.debug(f"Default components registered successfully. Registry info: {json.dumps(registry.get_info().model_dump(), indent=2)}")
except Exception as e:
    logger.error(f"Error initializing registry: {str(e)}")
