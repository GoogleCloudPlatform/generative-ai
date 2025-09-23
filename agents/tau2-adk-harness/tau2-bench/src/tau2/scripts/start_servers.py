#!/usr/bin/env python3
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
from loguru import logger


def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    try:
        for proc in psutil.process_iter():
            try:
                # Get connections for the process
                connections = proc.net_connections()
                for conn in connections:
                    if hasattr(conn, "laddr") and conn.laddr.port == port:
                        logger.warning(
                            f"Killing existing process {proc.pid} on port {port}"
                        )
                        proc.terminate()
                        time.sleep(0.5)  # Give it a moment to terminate
                        if proc.is_running():  # If still running
                            proc.kill()  # Force kill
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.debug(f"Error checking process {proc.pid}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error while trying to kill process on port {port}: {e}")
    return False


def run_server(command, port):
    """Run a server command with proper cleanup handling."""
    # First kill any existing process on the port
    kill_process_on_port(port)

    process = None
    try:
        process = subprocess.Popen(command, shell=True)
        process.wait()
    except KeyboardInterrupt:
        logger.info(f"\nShutting down server on port {port}...")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command '{command}': {e}")
    finally:
        if process and process.poll() is None:
            try:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:  # If still running
                    process.kill()  # Force kill
            except Exception as e:
                logger.error(f"Error while terminating process: {e}")
        # Double check if anything is still on the port
        kill_process_on_port(port)


def main():
    # Define server commands with their ports
    servers = [
        ("sh scripts/start_tau2_server.sh", 8001),
    ]

    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info("\nReceived shutdown signal, cleaning up...")
        # Only clean up the tau2 server port since React script handles its own cleanup
        kill_process_on_port(8001)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Tau2 server...")
    try:
        with ThreadPoolExecutor(max_workers=len(servers)) as executor:
            # Start each server in a separate thread
            futures = [
                executor.submit(run_server, command, port) for command, port in servers
            ]

            # Wait for all servers to complete
            for future in futures:
                future.result()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
    finally:
        # Cleanup on exit - only clean up tau2 server
        logger.info("Cleaning up...")
        kill_process_on_port(8001)


if __name__ == "__main__":
    main()
