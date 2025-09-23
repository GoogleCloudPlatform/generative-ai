#!/usr/bin/env python3
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.prompt import IntPrompt, Prompt
from rich.text import Text

from tau2.data_model.simulation import Results
from tau2.metrics.agent_metrics import compute_metrics, is_successful
from tau2.utils.display import ConsoleDisplay
from tau2.utils.utils import DATA_DIR


def get_available_simulations():
    """Get list of available simulation result files."""
    sim_dir = Path(DATA_DIR) / "simulations"
    if not sim_dir.exists():
        return []

    return sorted([f for f in sim_dir.glob("*.json")])


def display_simulation_list(
    results: Results, only_show_failed: bool = False, only_show_all_failed: bool = False
):
    """Display a numbered list of simulations with basic info."""
    ConsoleDisplay.console.print("\n[bold blue]Available Simulations:[/]")

    # calculate number of successful and total trials for each task
    num_success = defaultdict(int)
    for sim in results.simulations:
        if is_successful(sim.reward_info.reward):
            num_success[sim.task_id] += 1

    for i, sim in enumerate(results.simulations, 1):
        reward = sim.reward_info.reward if sim.reward_info else None

        # filter out simulations based on the flags
        if only_show_failed:
            if is_successful(reward):
                continue
        if only_show_all_failed:
            if num_success[sim.task_id] > 0:
                continue

        reward_str = "✅" if is_successful(reward) else "❌"
        db_match = "N/A"
        if sim.reward_info and sim.reward_info.db_check:
            db_match = "YES" if sim.reward_info.db_check.db_match else "NO"

        # Create text with task ID
        task_text = Text()
        task_text.append(f"{i}.", style="cyan")
        task_text.append(" Task: ")
        task_text.append(sim.task_id)  # This will display square brackets correctly
        task_text.append(
            f" | Trial: {sim.trial} | Reward: {reward_str} | Duration: {sim.duration:.2f}s | DB Match: {db_match} | "
        )

        ConsoleDisplay.console.print(task_text)

    if only_show_all_failed:
        num_all_failed = len([1 for v in num_success.values() if v == 0])
        ConsoleDisplay.console.print(f"Total number of failed trials: {num_all_failed}")


def display_available_files(files):
    """Display a numbered list of available simulation files."""
    ConsoleDisplay.console.print("\n[bold blue]Available Simulation Files:[/]")
    for i, file in enumerate(files, 1):
        ConsoleDisplay.console.print(f"[cyan]{i}.[/] {file.name}")


def display_simulation_with_task(
    simulation, task, results_file: str, sim_index: int, show_details: bool = True
):
    """Display a simulation along with its associated task."""
    ConsoleDisplay.console.print("\n" + "=" * 80)  # Separator
    ConsoleDisplay.console.print("[bold blue]Task Details:[/]")
    ConsoleDisplay.display_task(task)

    ConsoleDisplay.console.print("\n" + "=" * 80)  # Separator
    ConsoleDisplay.console.print("[bold blue]Simulation Details:[/]")
    ConsoleDisplay.display_simulation(simulation, show_details=show_details)

    # Prompt for notes
    ConsoleDisplay.console.print("\n" + "=" * 80)  # Separator
    ConsoleDisplay.console.print("[bold blue]Add Notes:[/]")
    note = Prompt.ask("Enter your notes about this simulation (press Enter to skip)")

    if note.strip():
        save_simulation_note(simulation, task, note, results_file, sim_index)
        ConsoleDisplay.console.print("[green]Note saved successfully![/]")


def parse_key(key: str) -> tuple[str, int]:
    """Parse a key into a task ID and trial number."""
    task_id, trial = key.split("-")
    return task_id, int(trial)


def find_task_by_id(tasks, task_id):
    """Find a task in the task list by its ID."""
    for task in tasks:
        if task.id == task_id:
            return task
    return None


def find_simulation_by_task_id_and_trial(results, task_id, trial):
    """Get a simulation by its task ID and trial number."""
    return next(
        (
            sim
            for sim in results.simulations
            if sim.task_id == task_id and sim.trial == trial
        ),
        None,
    )


def save_simulation_note(
    simulation, task, note: str, results_file: str, sim_index: int
):
    """Save a note about a simulation to a CSV file."""
    notes_file = Path(DATA_DIR) / "simulations" / "simulation_notes.csv"
    file_exists = notes_file.exists()

    # Prepare the row data
    row = {
        "timestamp": datetime.now().isoformat(),
        "simulation_id": simulation.id,
        "task_id": simulation.task_id,
        "trial": simulation.trial,
        "duration": simulation.duration,
        "reward": simulation.reward_info.reward if simulation.reward_info else None,
        "db_match": simulation.reward_info.db_check.db_match
        if simulation.reward_info and simulation.reward_info.db_check
        else None,
        "results_file": results_file,
        "sim_index": sim_index,
        "note": note,
    }

    # Write to CSV file
    with open(notes_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main(
    sim_file: Optional[str] = None,
    only_show_failed: bool = False,
    only_show_all_failed: bool = False,
):
    # Get available simulation files
    if sim_file is None:
        sim_files = get_available_simulations()
    else:
        sim_files = [Path(sim_file)]

    if not sim_files:
        ConsoleDisplay.console.print(
            "[red]No simulation files found in data/simulations/[/]"
        )
        return

    results = None
    current_file = None
    while True:
        # Show main menu
        ConsoleDisplay.console.print("\n[bold yellow]Main Menu:[/]")
        ConsoleDisplay.console.print("1. Select simulation file")
        ConsoleDisplay.console.print(
            "   [dim]Choose a simulation results file to load and analyze[/]"
        )
        if results:
            ConsoleDisplay.console.print("2. View agent performance metrics")
            ConsoleDisplay.console.print("   [dim]Display agent performance metrics[/]")
            ConsoleDisplay.console.print("3. View simulation")
            ConsoleDisplay.console.print(
                "   [dim]Examine a specific simulation in detail with all its data[/]"
            )
            ConsoleDisplay.console.print("4. View task details")
            ConsoleDisplay.console.print(
                "   [dim]Look at the configuration and parameters of a specific task[/]"
            )
            ConsoleDisplay.console.print("5. Exit")
            ConsoleDisplay.console.print("   [dim]Close the simulation viewer[/]")
            choices = ["1", "2", "3", "4", "5"]
            default_choice = "3"
        else:
            ConsoleDisplay.console.print("2. Exit")
            ConsoleDisplay.console.print("   [dim]Close the simulation viewer[/]")
            choices = ["1", "2"]
            default_choice = "1"

        choice = Prompt.ask(
            "\nWhat would you like to do?", choices=choices, default=default_choice
        )

        if choice == "1":
            # Show available files and get selection
            display_available_files(sim_files)
            # default to view the last file
            file_num = IntPrompt.ask(
                f"\nSelect file number (1-{len(sim_files)})", default=len(sim_files)
            )

            if 1 <= file_num <= len(sim_files):
                try:
                    current_file = sim_files[file_num - 1].name
                    results = Results.load(sim_files[file_num - 1])
                    ConsoleDisplay.console.print(
                        f"\n[bold green]Loaded {len(results.simulations)} simulations from {current_file}[/]"
                    )
                    results.simulations = sorted(
                        results.simulations, key=lambda x: (x.task_id, x.trial)
                    )
                except Exception as e:
                    ConsoleDisplay.console.print(
                        f"[red]Error loading results:[/] {str(e)}"
                    )
            else:
                ConsoleDisplay.console.print("[red]Invalid file number[/]")

        elif choice == "2" and not results:
            break

        elif results and choice == "2":
            # Display metrics
            ConsoleDisplay.console.clear()
            metrics = compute_metrics(results)
            ConsoleDisplay.display_agent_metrics(metrics)
            continue

        elif results and choice == "3":
            # Show list of simulations
            display_simulation_list(results, only_show_failed, only_show_all_failed)

            # Get simulation selection by index
            sim_count = len(results.simulations)
            sim_index = IntPrompt.ask(
                f"\nEnter simulation number (1-{sim_count})", default=1
            )

            if 1 <= sim_index <= sim_count:
                sim = results.simulations[sim_index - 1]
                task = find_task_by_id(results.tasks, sim.task_id)
                if task:
                    display_simulation_with_task(
                        sim, task, current_file, sim_index, show_details=True
                    )
                else:
                    ConsoleDisplay.console.print(
                        f"[red]Warning: Could not find task for simulation {sim.id}[/]"
                    )
                    ConsoleDisplay.display_simulation(sim, show_details=True)
                continue
            else:
                ConsoleDisplay.console.print("[red]Invalid simulation number[/]")
                continue

        elif results and choice == "4":
            # Show list of tasks
            ConsoleDisplay.console.print("\n[bold blue]Available Tasks:[/]")
            for i, task in enumerate(results.tasks, 1):
                task_text = Text()
                task_text.append(f"{i}.", style="cyan")
                task_text.append(" Task ID: ")
                task_text.append(task.id)  # This will display square brackets correctly
                ConsoleDisplay.console.print(task_text)

            # Get task selection
            task_count = len(results.tasks)
            task_num = IntPrompt.ask(f"\nEnter task number (1-{task_count})", default=1)

            if 1 <= task_num <= task_count:
                ConsoleDisplay.console.clear()
                ConsoleDisplay.display_task(results.tasks[task_num - 1])
                continue
            else:
                ConsoleDisplay.console.print("[red]Invalid task number[/]")
                continue

        else:  # Exit options
            break

    ConsoleDisplay.console.print("\n[green]Thanks for using the simulation viewer![/]")


if __name__ == "__main__":
    main()
