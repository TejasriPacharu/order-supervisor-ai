import asyncio
import uuid

from temporalio.client import Client

from workflows import OrderSupervisorWorkflow

TASK_QUEUE = "order-supervisor"
TEMPORAL_ADDRESS = "localhost:7233"


async def main():
    client = await Client.connect(TEMPORAL_ADDRESS)

    #Start a new workflow
    workflow_id = f"order-supervisor-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        OrderSupervisorWorkflow.run,
        {
            "run_id": workflow_id,
            "order_id": "ORD-12345",
            "supervisor_config": {
                "model": "gpt-4o",
                "max_retries": 3,
            },
        },
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"Started workflow: {workflow_id}")

    #Send an event signal
    await handle.signal(
        OrderSupervisorWorkflow.new_event,
        {"type": "status_update", "data": {"status": "shipped"}},
    )
    print("Sent 'status_update' event")

    #Add an instruction 
    await handle.signal(
        OrderSupervisorWorkflow.add_instruction,
        "Prioritize contacting the customer about the delay.",
    )
    print("Sent extra instruction")

    #Query current state
    state = await handle.query(OrderSupervisorWorkflow.get_state)
    print(f"Current state: {state}")

    #Send a terminal event to finish the workflow 
    await handle.signal(
        OrderSupervisorWorkflow.new_event,
        {"type": "delivered", "data": {}},
    )
    print("Sent 'delivered' (terminal) event — workflow will complete")

    result = await handle.result()
    print(f"Workflow finished: {result}")


if __name__ == "__main__":
    asyncio.run(main())