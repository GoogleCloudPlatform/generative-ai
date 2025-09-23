# FILE: run_evaluation.py

import asyncio
import argparse
import importlib
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from copy import deepcopy

# --- ADK Imports ---
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai.types import Content, Part, FunctionResponse, FunctionCall

# --- Tau2-Bench Imports ---
from tau2.run import get_tasks
from tau2.registry import registry
from tau2.evaluator.evaluator_env import EnvironmentEvaluator
from tau2.data_model.simulation import SimulationRun, TerminationReason
from tau2.data_model.message import UserMessage, AssistantMessage, ToolCall, ToolMessage
from tau2.user.user_simulator import UserSimulator

# --- Harness Imports ---
from harness.tool_mapper import get_tool_mapping

def _find_tool_call_in_events(events: list) -> FunctionCall | None:
    """Helper to find the first tool call in a list of ADK events."""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    return part.function_call
    return None

def _get_final_text_from_events(events: list) -> str | None:
    """Helper to find and concatenate the final text response from a list of ADK events."""
    final_text = ""
    for event in events:
        if event.is_final_response() and event.content and event.content.parts and event.content.parts[0].text:
            final_text += event.content.parts[0].text
    return final_text if final_text else None


async def run_evaluation_for_task(domain: str, task, adk_agent, user_llm: str):
    """Orchestrates the evaluation of a single task in a conversational manner."""
    print(f"--- Running Task: {task.id} ---")

    env_constructor = registry.get_env_constructor(domain)
    tau2_env = env_constructor()
    if task.initial_state:
        tau2_env.set_state(
            initialization_data=task.initial_state.initialization_data,
            initialization_actions=task.initial_state.initialization_actions,
            message_history=task.initial_state.message_history or [],
        )

    domain_policy = tau2_env.get_policy()
    adk_agent_with_policy = deepcopy(adk_agent)
    original_instruction = adk_agent_with_policy.instruction
    adk_agent_with_policy.instruction = (
        "You must strictly follow the policies provided below.\n\n"
        "<policy>\n"
        f"{domain_policy}\n"
        "</policy>\n\n"
        "--- Your Original Instructions ---\n"
        f"{original_instruction}"
    )
    print("\n[INFO] Injected Tau2 domain policy into ADK agent's instructions for this run.")

    adk_session_service = InMemorySessionService()
    adk_runner = Runner(agent=adk_agent_with_policy, app_name="adk_eval_harness", session_service=adk_session_service)
    adk_session = await adk_session_service.create_session(app_name="adk_eval_harness", user_id="eval_user")

    user_simulator = UserSimulator(instructions=str(task.user_scenario), llm=user_llm)
    user_sim_state = user_simulator.get_init_state()
    
    tau2_trajectory = []

    initial_assistant_msg = AssistantMessage(role="assistant", content="Hello! How can I help you today?")
    user_response_msg, user_sim_state = user_simulator.generate_next_message(initial_assistant_msg, user_sim_state)
    
    print(f"\n[USER SIMULATOR]: {user_response_msg.content}")
    tau2_trajectory.append(user_response_msg)
    current_adk_message = Content(role="user", parts=[Part(text=user_response_msg.content)])

    for turn in range(15):
        print(f"\n>>> Turn {turn+1}: ADK Agent processing...")
        
        adk_events = [event async for event in adk_runner.run_async(
            session_id=adk_session.id, 
            user_id="eval_user", 
            new_message=current_adk_message
        )]

        adk_tool_call = _find_tool_call_in_events(adk_events)

        if adk_tool_call:
            tool_map_config = get_tool_mapping(domain)
            adk_tool_name = adk_tool_call.name
            adk_args = dict(adk_tool_call.args)
            adk_tool_call_id = adk_tool_call.id or f"adk_tool_call_{turn}"
            
            print(f"  [ADK AGENT -> Harness]: Tool Call: {adk_tool_name}({adk_args})")

            tau2_tool_name = tool_map_config["tool_map"].get(adk_tool_name)
            tau2_args = tool_map_config["arg_mapper"](adk_tool_name, adk_args)
            
            tau2_trajectory.append(AssistantMessage(role="assistant", tool_calls=[
                ToolCall(id=adk_tool_call_id, name=tau2_tool_name, arguments=tau2_args)
            ]))
            
            tool_result = tau2_env.use_tool(tool_name=tau2_tool_name, **tau2_args)
            print(f"  [Harness -> Tau2 Env]: Executed {tau2_tool_name}.")
            
            # This block now correctly handles all tool result types for both
            # the ADK agent's next turn and the evaluation trajectory.
            if hasattr(tool_result, 'model_dump'):
                # This is a Pydantic object, serialize it to a dict
                tool_result_for_adk = tool_result.model_dump()
                tool_result_for_eval = tool_result.model_dump()
            elif isinstance(tool_result, dict):
                # It's already a dict
                tool_result_for_adk = tool_result
                tool_result_for_eval = tool_result
            else:
                # It's a primitive (like a string), wrap it for ADK
                # but keep it raw for the evaluator.
                tool_result_for_adk = {"result": tool_result}
                tool_result_for_eval = tool_result

            tau2_trajectory.append(ToolMessage(
                id=adk_tool_call_id,
                role="tool",
                content=json.dumps(tool_result_for_eval),
                requestor="assistant"
            ))

            current_adk_message = Content(role="user", parts=[
                Part(function_response=FunctionResponse(id=adk_tool_call_id, name=adk_tool_name, response=tool_result_for_adk))
            ])
            continue
        
        else:
            final_text = _get_final_text_from_events(adk_events)
            if not final_text:
                final_text = "(Agent produced no text response)"
            
            print(f"  [ADK AGENT -> User]: {final_text}")
            
            agent_response_msg = AssistantMessage(role="assistant", content=final_text)
            tau2_trajectory.append(agent_response_msg)

            user_response_msg, user_sim_state = user_simulator.generate_next_message(agent_response_msg, user_sim_state)

            if UserSimulator.is_stop(user_response_msg):
                print(f"\n[USER SIMULATOR]: {user_response_msg.content} (STOP SIGNAL)")
                tau2_trajectory.append(user_response_msg)
                break
            
            print(f"\n[USER SIMULATOR]: {user_response_msg.content}")
            tau2_trajectory.append(user_response_msg)
            current_adk_message = Content(role="user", parts=[Part(text=user_response_msg.content)])

    print("\n--- CONVERSATION TRAJECTORY (for evaluation replay) ---")
    for msg in tau2_trajectory:
        print(f"[{msg.role.upper()}]")
        if msg.content:
            print(f"  Content: {msg.content}")
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  Tool Call: {tc.name}({json.dumps(tc.arguments)})")
    print("-----------------------------\n")

    dummy_sim_run = SimulationRun(
        id="adk_harness_run", task_id=task.id, start_time="", end_time="", duration=0,
        termination_reason=TerminationReason.USER_STOP,
        messages=tau2_trajectory
    )
    
    reward_info = EnvironmentEvaluator.calculate_reward(
        environment_constructor=env_constructor,
        task=task,
        full_trajectory=dummy_sim_run.messages
    )

    print("\n--- EVALUATION RESULT ---")
    print(f"✅ Task: {task.id}")
    print(f"🏆 Reward: {reward_info.reward:.2f}")
    if reward_info.db_check:
        print(f"🗃️ DB Match: {reward_info.db_check.db_match}")
    print("----------------------------\n")

async def main(args):
    agent_path_str = args.adk_agent_path
    
    try:
        file_path_str, agent_variable_name = agent_path_str.split(":")
    except ValueError:
        raise ValueError(f"Invalid --adk_agent_path format. Expected 'path/to/agent.py:variable_name', but got '{agent_path_str}'")

    agent_file_path = Path(file_path_str).resolve()
    if not agent_file_path.is_file():
        raise FileNotFoundError(f"Agent file not found at: {agent_file_path}")

    agent_dir = agent_file_path.parent
    sys.path.insert(0, str(agent_dir))

    try:
        module_name = agent_file_path.stem
        agent_module = importlib.import_module(module_name)
        adk_agent = getattr(agent_module, agent_variable_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import agent '{agent_variable_name}' from '{agent_file_path}'. Error: {e}")
    finally:
        sys.path.pop(0)

    tasks = get_tasks(args.domain, num_tasks=args.num_tasks)
    
    for task in tasks:
        await run_evaluation_for_task(args.domain, task, adk_agent, args.user_llm)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Conversational ADK Agent Evaluation Harness")
    parser.add_argument("--domain", type=str, required=True, help="Tau2-Bench domain to evaluate")
    parser.add_argument("--num-tasks", type=int, default=3, help="Number of tasks to run.")
    parser.add_argument("--adk_agent_path", type=str, required=True, help="Path to ADK agent. e.g., 'sample_adk_agent/my_agent/agent.py:root_agent'")
    parser.add_argument("--user-llm", type=str, required=True, help="LLM to use for the user simulator.")
    
    args = parser.parse_args()
    
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")

    asyncio.run(main(args))