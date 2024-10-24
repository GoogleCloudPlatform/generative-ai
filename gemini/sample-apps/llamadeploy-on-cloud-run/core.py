from llama_deploy import ControlPlaneConfig, SimpleMessageQueueConfig, deploy_core


async def main() -> None:
    """Launches the core services required for the Llama workflow application."""
    await deploy_core(
        control_plane_config=ControlPlaneConfig(host="0.0.0.0", port=8000),
        message_queue_config=SimpleMessageQueueConfig(host="0.0.0.0", port=8001),
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
