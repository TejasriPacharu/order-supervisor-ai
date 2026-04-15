import json
import logging
import random
from datetime import datetime

from temporalio import activity

from api.database import SessionLocal
from api.models import Activity, Run

logger = logging.getLogger(__name__)

ACTION_TOOLS = {"message_fulfillment_team", "message_payments_team", "message_logistics_team", "message_customer", "create_internal_note"}

EVENT_RESPONSES = {
    "order_created": {
        "reasoning": "New order received. Initializing monitoring. Will track payment status next.",
        "actions": [("create_internal_note", {"note": "Order supervision started. Monitoring for payment confirmation."})],
        "state_updates": {"phase": "awaiting_payment", "priority": "normal"},
        "sleep": 120,
    },
    "payment_confirmed": {
        "reasoning": "Payment confirmed. Order is progressing normally. Will monitor for shipment creation.",
        "actions": [
            ("message_fulfillment_team", {"message": "Payment confirmed. Please proceed with order fulfillment."}),
            ("create_internal_note", {"note": "Payment received successfully."}),
        ],
        "state_updates": {"phase": "awaiting_shipment", "payment_status": "confirmed"},
        "sleep": 300,
    },
    "payment_failed": {
        "reasoning": "Payment failed. This is urgent. Notifying payments team and customer immediately.",
        "actions": [
            ("message_payments_team", {"message": "Payment failed for this order. Please investigate and retry."}),
            ("message_customer", {"message": "We noticed an issue with your payment. Our team is looking into it."}),
            ("create_internal_note", {"note": "Payment failure detected. Escalated to payments team."}),
        ],
        "state_updates": {"phase": "payment_issue", "priority": "high", "payment_status": "failed"},
        "sleep": 60,
    },
    "shipment_created": {
        "reasoning": "Shipment created. Order is on track. Monitoring for delivery.",
        "actions": [
            ("message_customer", {"message": "Your order has been shipped! You will receive tracking details soon."}),
            ("create_internal_note", {"note": "Shipment created. Tracking delivery progress."}),
        ],
        "state_updates": {"phase": "in_transit", "shipment_status": "created"},
        "sleep": 600,
    },
    "shipment_delayed": {
        "reasoning": "Shipment delayed. Contacting logistics team for update and informing customer.",
        "actions": [
            ("message_logistics_team", {"message": "Shipment is delayed. Please provide an updated ETA."}),
            ("message_customer", {"message": "Your shipment is experiencing a delay. We are working to resolve this."}),
            ("create_internal_note", {"note": "Shipment delay detected. Escalated to logistics."}),
        ],
        "state_updates": {"phase": "delayed", "priority": "high", "shipment_status": "delayed"},
        "sleep": 120,
    },
    "delivered": {
        "reasoning": "Order delivered successfully. Closing supervision.",
        "actions": [
            ("message_customer", {"message": "Your order has been delivered. Thank you for your purchase!"}),
            ("create_internal_note", {"note": "Order delivered. Run complete."}),
        ],
        "state_updates": {"phase": "delivered", "shipment_status": "delivered"},
        "sleep": 0,
    },
    "refund_requested": {
        "reasoning": "Refund requested. Alerting payments team and logging for review.",
        "actions": [
            ("message_payments_team", {"message": "Customer has requested a refund. Please process."}),
            ("message_customer", {"message": "We received your refund request. Our team will process it shortly."}),
            ("create_internal_note", {"note": "Refund requested by customer. Forwarded to payments team."}),
        ],
        "state_updates": {"phase": "refund_pending", "priority": "high"},
        "sleep": 120,
    },
    "customer_message_received": {
        "reasoning": "Customer message received. Reviewing and acknowledging.",
        "actions": [
            ("create_internal_note", {"note": "Customer message received. Reviewing content."}),
            ("message_customer", {"message": "Thank you for reaching out. We are reviewing your message."}),
        ],
        "state_updates": {"last_customer_contact": "received"},
        "sleep": 180,
    },
    "no_update_for_n_hours": {
        "reasoning": "No updates for a while. Checking in with relevant teams.",
        "actions": [
            ("message_fulfillment_team", {"message": "Checking in on order status. Any updates?"}),
            ("create_internal_note", {"note": "No updates received. Proactively checking in."}),
        ],
        "state_updates": {"last_checkin": "proactive"},
        "sleep": 600,
    },
}

DEFAULT_RESPONSE = {
    "reasoning": "Received update. Monitoring situation. No immediate action needed.",
    "actions": [("create_internal_note", {"note": "Event received and acknowledged."})],
    "state_updates": {},
    "sleep": 300,
}


def record_activity(db, run_id: str, activity_type: str, data: dict):
    db.add(Activity(run_id=run_id, type=activity_type, data=data))
    db.commit()


def execute_mock_actions(db, run_id: str, actions: list, state: dict):
    for action_name, action_input in actions:
        record_activity(db, run_id, "action", {"action": action_name, **action_input})

    for key, value in state.items():
        pass


def get_latest_event_type(ctx: dict) -> str:
    events = ctx.get("events", [])
    if events:
        return events[-1].get("type", "unknown")
    return ctx.get("trigger", "scheduled_wakeup")


@activity.defn
async def run_agent(ctx: dict) -> dict:
    db = SessionLocal()
    try:
        state = dict(ctx.get("agent_state", {}))
        record_activity(db, ctx["run_id"], "wake", {"trigger": ctx["trigger"], "events": ctx.get("events", [])})

        event_type = get_latest_event_type(ctx)
        mock = EVENT_RESPONSES.get(event_type, DEFAULT_RESPONSE)

        for action_name, action_input in mock["actions"]:
            record_activity(db, ctx["run_id"], "action", {"action": action_name, **action_input})

        state.update(mock["state_updates"])
        sleep_seconds = mock["sleep"] or 300

        reasoning = mock["reasoning"]
        if ctx.get("extra_instructions"):
            reasoning += f" (Noted additional instructions: {', '.join(ctx['extra_instructions'])})"

        record_activity(db, ctx["run_id"], "decision", {"decision": "reasoning", "text": reasoning})
        record_activity(db, ctx["run_id"], "decision", {"decision": "sleep", "seconds": sleep_seconds})

        run = db.get(Run, ctx["run_id"])
        if run:
            run.state = state
            db.commit()

        logger.info("Agent completed for run %s, sleep=%ds", ctx["run_id"], sleep_seconds)
        return {"state": state, "sleep_seconds": sleep_seconds, "reasoning": reasoning}
    finally:
        db.close()


@activity.defn
async def generate_summary(ctx: dict) -> dict:
    db = SessionLocal()
    try:
        activities = db.query(Activity).filter(Activity.run_id == ctx["run_id"]).order_by(Activity.created_at).all()
        action_count = sum(1 for a in activities if a.type == "action")
        event_count = sum(1 for a in activities if a.type == "event")
        state = ctx.get("agent_state", {})

        summary_text = (
            f"## Final Summary\n\n"
            f"Order {ctx['order_id']} supervision completed with status: {ctx.get('status', 'completed')}.\n"
            f"Processed {event_count} events and took {action_count} actions.\n"
            f"Final state: {json.dumps(state)}\n\n"
            f"## Important Actions Taken\n\n"
            f"- Monitored order through {state.get('phase', 'unknown')} phase\n"
            f"- Communicated with relevant teams as needed\n"
            f"- Maintained proactive monitoring schedule\n\n"
            f"## Key Learnings\n\n"
            f"- Order required {'elevated' if state.get('priority') == 'high' else 'standard'} attention\n"
            f"- {'Delays were encountered and escalated' if state.get('shipment_status') == 'delayed' else 'Order progressed without major issues'}\n\n"
            f"## Recommendations\n\n"
            f"- Continue monitoring similar orders for patterns\n"
            f"- {'Review delay handling procedures' if state.get('shipment_status') == 'delayed' else 'Current processes are working well'}\n"
        )

        record_activity(db, ctx["run_id"], "summary", {"summary": summary_text})

        run = db.get(Run, ctx["run_id"])
        if run:
            run.final_summary = summary_text
            run.completed_at = datetime.utcnow()
            db.commit()

        logger.info("Summary generated for run %s", ctx["run_id"])
        return {"summary": summary_text}
    finally:
        db.close()


@activity.defn
async def sync_run_status(run_id: str, status: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run:
            run.status = status
            if status in ("completed", "terminated"):
                run.completed_at = run.completed_at or datetime.utcnow()
            db.commit()
        logger.info("Run %s status synced to %s", run_id, status)
    finally:
        db.close()
