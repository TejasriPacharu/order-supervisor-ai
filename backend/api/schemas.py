from pydantic import BaseModel


class SupervisorCreate(BaseModel):
    name: str
    base_instruction: str
    actions: list[str] = [
        "message_fulfillment_team",
        "message_payments_team",
        "message_logistics_team",
        "message_customer",
        "create_internal_note",
    ]
    wake_behavior: str = "normal"
    model: str = "claude-sonnet-4-20250514"
    wake_aggressiveness: str = "medium"


class RunCreate(BaseModel):
    supervisor_id: str
    order_id: str


class EventCreate(BaseModel):
    type: str
    data: dict = {}


class InstructionCreate(BaseModel):
    instruction: str
