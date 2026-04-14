import json
import logging
from datetime import datetime

from temporalio import activity

logger = logging.getLogger(__name__)


MOCK_AGENT_RESPONSES = {
    "run_start": {
        "message": "Order received. Monitoring for updates.",
        "actions_taken": ["logged_order", "set_initial_watch"],
        "sleep_seconds": 10,
    },
    "event": {
        "message": "Processing incoming event.",
        "actions_taken": ["acknowledged_event"],
        "sleep_seconds": 10,
    },
    "scheduled_wakeup": {
        "message": "No new events. Checking order status.",
        "actions_taken": ["polled_status"],
        "sleep_seconds": 15,
    },
    "terminal_event": {
        "message": "Order delivered. Wrapping up.",
        "actions_taken": ["confirmed_delivery", "closed_ticket"],
        "sleep_seconds": 0,
    },
}


@activity.defn
async def run_agent(params: dict) -> dict:
    trigger = params["trigger"]
    agent_state = params["agent_state"]

    logger.info(
        "run_agent | run=%s trigger=%s events=%s",
        params["run_id"], trigger, params["events"],
    )

    mock = MOCK_AGENT_RESPONSES.get(trigger, MOCK_AGENT_RESPONSES["event"])

    log = agent_state.get("action_log", [])
    log.append({
        "ts": datetime.utcnow().isoformat(),
        "trigger": trigger,
        "mock_message": mock["message"],
    })

    return {
        "state": {**agent_state, "action_log": log, "last_message": mock["message"]},
        "sleep_seconds": mock["sleep_seconds"],
    }


@activity.defn
async def generate_summary(params: dict) -> dict:
    state = params["agent_state"]
    summary = {
        "run_id": params["run_id"],
        "order_id": params["order_id"],
        "status": params["status"],
        "invocations": len(state.get("action_log", [])),
        "last_message": state.get("last_message", ""),
    }
    logger.info("Summary: %s", json.dumps(summary))
    return summary


@activity.defn
async def sync_run_status(run_id: str, status: str) -> None:
    logger.info("sync_run_status | %s -> %s", run_id, status)