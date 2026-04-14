import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from activities import generate_summary, run_agent, sync_run_status
from workflows import OrderSupervisorWorkflow

TASK_QUEUE = "order-supervisor"
TEMPORAL_ADDRESS = "localhost:7233"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Connecting to Temporal at %s …", TEMPORAL_ADDRESS)
    client = await Client.connect(TEMPORAL_ADDRESS)

    logger.info("Starting worker on queue %r", TASK_QUEUE)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[OrderSupervisorWorkflow],
        activities=[run_agent, generate_summary, sync_run_status],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())