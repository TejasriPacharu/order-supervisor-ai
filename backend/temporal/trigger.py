import asyncio
import json
import logging
import os
import sys

from temporalio.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ACTIONS = {
    "event": lambda handle, data: handle.signal("new_event", json.loads(data)),
    "instruction": lambda handle, data: handle.signal("add_instruction", data),
    "terminate": lambda handle, _: handle.signal("set_status", "terminated"),
    "pause": lambda handle, _: handle.signal("set_status", "paused"),
    "resume": lambda handle, _: handle.signal("set_status", "active"),
}


async def main():
    action, workflow_id = sys.argv[1], sys.argv[2]
    data = sys.argv[3] if len(sys.argv) > 3 else ""

    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    handle = client.get_workflow_handle(workflow_id)

    if action == "query":
        result = await handle.query("get_state")
        logger.info("Workflow state: %s", json.dumps(result, indent=2))
        return

    if action not in ACTIONS:
        logger.error("Unknown action: %s. Use: %s", action, ", ".join(ACTIONS))
        return

    await ACTIONS[action](handle, data)
    logger.info("Sent %s to %s", action, workflow_id)


if __name__ == "__main__":
    asyncio.run(main())
