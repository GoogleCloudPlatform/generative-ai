#!/bin/bash
# Run the full pipeline per user: cleanup → generate swarm → sample eval → evaluate
# Usage:
#   ./run_pipeline.sh                    # all users (1,2,3,4,5)
#   ./run_pipeline.sh user_1 user_3      # specific users only
#   ./run_pipeline.sh --skip-critic      # skip critic pass (faster)

set -e

cd "$(dirname "$0")"

# Ensure the uv-managed environment exists and is in sync with pyproject.toml/uv.lock
uv sync --quiet

# ANSI colors
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BOLD='\033[1m'
RESET='\033[0m'

# Parse arguments
USERS=()
SKIP_CRITIC=""
for arg in "$@"; do
    if [[ "$arg" == "--skip-critic" ]]; then
        SKIP_CRITIC="--skip-critic"
    else
        USERS+=("$arg")
    fi
done

# Default to users 1,2,3,4,5 if none specified
if [[ ${#USERS[@]} -eq 0 ]]; then
    USERS=(user_1 user_2 user_3 user_4 user_5)
fi

echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD}  Per-User Pipeline: Generate → Sample → Evaluate${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo -e "Users: ${USERS[*]}"
echo -e "Critic: ${SKIP_CRITIC:-enabled}"
echo ""

PASSED=()
FAILED=()

for user in "${USERS[@]}"; do
    echo -e "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}  ${user}${RESET}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

    # Step 1: Cleanup stale outputs
    echo -e "\n${YELLOW}[$user]${RESET} Step 1/4: Cleanup"
    swarm_agents_dir="swarms/${user}/agents"
    if [[ -d "$swarm_agents_dir" ]]; then
        echo -e "  Removing stale swarm agents: ${swarm_agents_dir}/"
        rm -rf "$swarm_agents_dir"
    fi
    pycache_dir="swarms/${user}/__pycache__"
    if [[ -d "$pycache_dir" ]]; then
        rm -rf "$pycache_dir"
    fi
    echo -e "  ${GREEN}Clean${RESET}"

    # Step 2: Analyze history and generate swarm
    echo -e "\n${YELLOW}[$user]${RESET} Step 2/4: Swarm generation"
    if ! uv run python analyzer/analyze_history.py --user "$user" --verbose $SKIP_CRITIC; then
        echo -e "${RED}FAILED: $user swarm generation${RESET}"
        FAILED+=("$user")
        continue
    fi
    echo -e "  ${GREEN}Swarm generated${RESET}"

    # Step 3: Sample eval scenarios from pool (if pool exists)
    echo -e "\n${YELLOW}[$user]${RESET} Step 3/4: Sample eval scenarios"
    eval_file="evaluation_scenarios_${user}.json"
    pool_file="eval_pool/${user}/pool.json"
    if [[ -f "$pool_file" ]]; then
        echo -e "  Sampling from pool (with LLM review)..."
        if ! uv run python eval/sample_eval_scenarios.py --user "$user" --seed 42; then
            echo -e "  ${YELLOW}Sampling failed — falling back to existing eval file${RESET}"
        else
            echo -e "  ${GREEN}Eval scenarios sampled${RESET}"
        fi
    else
        echo -e "  ${YELLOW}No pool at $pool_file — using existing eval file${RESET}"
    fi

    # Step 4: Run evaluation with judge
    echo -e "\n${YELLOW}[$user]${RESET} Step 4/4: Evaluation"
    if [[ ! -f "$eval_file" ]]; then
        echo -e "  ${RED}Skipping evaluation — no eval file: $eval_file${RESET}"
        PASSED+=("$user (no eval)")
        continue
    fi
    if ! uv run python test_augmented_agent.py --eval-file "$eval_file" --judge --verbose; then
        echo -e "${RED}FAILED: $user evaluation${RESET}"
        FAILED+=("$user")
        continue
    fi
    echo -e "  ${GREEN}Evaluation complete${RESET}"

    PASSED+=("$user")
done

# Summary
echo -e "\n\n${BOLD}========================================${RESET}"
echo -e "${BOLD}  Pipeline Summary${RESET}"
echo -e "${BOLD}========================================${RESET}"
if [[ ${#PASSED[@]} -gt 0 ]]; then
    echo -e "${GREEN}Passed: ${PASSED[*]}${RESET}"
fi
if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo -e "${RED}Failed: ${FAILED[*]}${RESET}"
fi
echo -e "Results in: evaluation_output/"
echo -e "${BOLD}========================================${RESET}"

# Exit with error if any user failed
if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
