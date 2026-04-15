import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from temporal.activities import generate_summary, run_agent, sync_run_status
from temporal.workflows import OrderSupervisorWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    worker = Worker(
        client,
        task_queue="order-supervisor",
        workflows=[OrderSupervisorWorkflow],
        activities=[run_agent, generate_summary, sync_run_status],
    )
    logger.info("Worker started on task queue 'order-supervisor'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
