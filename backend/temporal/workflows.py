from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities import generate_summary, run_agent, sync_run_status

TERMINAL_EVENTS = {"delivered"}


@workflow.defn
class OrderSupervisorWorkflow:
    def __init__(self):
        self.pending_events: list[dict] = []
        self.extra_instructions: list[str] = []
        self.status = "active"
        self.agent_state: dict = {}
        self.sleep_seconds = 300

    @workflow.run
    async def run(self, params: dict):
        run_id = params["run_id"]
        order_id = params["order_id"]
        config = params["supervisor_config"]

        await self._invoke_agent(run_id, order_id, config, "run_start", [])
        await self._main_loop(run_id, order_id, config)
        await self._finalize(run_id, order_id, config)

    async def _main_loop(self, run_id, order_id, config):
        while self.status not in ("completed", "terminated"):
            has_events = await workflow.wait_condition(
                lambda: bool(self.pending_events) or self.status in ("completed", "terminated"),
                timeout=timedelta(seconds=self.sleep_seconds),
            )

            if self.status == "terminated":
                break

            if self.status == "completed":
                events = list(self.pending_events)
                self.pending_events.clear()
                await self._invoke_agent(run_id, order_id, config, "terminal_event", events)
                break

            if self.status == "paused":
                await workflow.wait_condition(lambda: self.status != "paused")
                continue

            trigger = "event" if has_events and self.pending_events else "scheduled_wakeup"
            events = list(self.pending_events)
            self.pending_events.clear()
            await self._invoke_agent(run_id, order_id, config, trigger, events)

    async def _invoke_agent(self, run_id, order_id, config, trigger, events):
        result = await workflow.execute_activity(
            run_agent,
            args=[{
                "run_id": run_id,
                "order_id": order_id,
                "trigger": trigger,
                "events": events,
                "agent_state": self.agent_state,
                "extra_instructions": self.extra_instructions,
                "supervisor_config": config,
            }],
            start_to_close_timeout=timedelta(minutes=5),
        )
        self.agent_state = result.get("state", self.agent_state)
        self.sleep_seconds = result.get("sleep_seconds", self.sleep_seconds)

    async def _finalize(self, run_id, order_id, config):
        await workflow.execute_activity(
            generate_summary,
            args=[{
                "run_id": run_id,
                "order_id": order_id,
                "agent_state": self.agent_state,
                "supervisor_config": config,
                "status": self.status,
            }],
            start_to_close_timeout=timedelta(minutes=2),
        )
        final_status = "terminated" if self.status == "terminated" else "completed"
        await workflow.execute_activity(
            sync_run_status,
            args=[run_id, final_status],
            start_to_close_timeout=timedelta(seconds=30),
        )

    @workflow.signal
    async def new_event(self, event: dict):
        self.pending_events.append(event)
        if event.get("type") in TERMINAL_EVENTS:
            self.status = "completed"

    @workflow.signal
    async def add_instruction(self, instruction: str):
        self.extra_instructions.append(instruction)
        self.pending_events.append({"type": "instruction_added", "data": {"instruction": instruction}})

    @workflow.signal
    async def set_status(self, status: str):
        self.status = status

    @workflow.query
    def get_state(self) -> dict:
        return {
            "status": self.status,
            "agent_state": self.agent_state,
            "pending_events": self.pending_events,
            "sleep_seconds": self.sleep_seconds,
        }
