import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from temporalio.client import Client

from api.database import Base, engine, get_db
from api.models import Activity, Run, Supervisor
from api.schemas import EventCreate, InstructionCreate, RunCreate, SupervisorCreate

logger = logging.getLogger(__name__)

temporal_client: Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global temporal_client
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    temporal_client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    logger.info("Connected to Temporal")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def serialize(obj) -> dict:
    d = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        d[c.name] = val.isoformat() if isinstance(val, datetime) else val
    return d


def serialize_with_activities(run: Run) -> dict:
    d = serialize(run)
    d["activities"] = [serialize(a) for a in run.activities]
    return d


@app.post("/api/supervisors")
def create_supervisor(body: SupervisorCreate, db: Session = Depends(get_db)):
    sup = Supervisor(**body.model_dump())
    db.add(sup)
    db.commit()
    db.refresh(sup)
    return serialize(sup)


@app.get("/api/supervisors")
def list_supervisors(db: Session = Depends(get_db)):
    return [serialize(s) for s in db.query(Supervisor).all()]


@app.get("/api/supervisors/{supervisor_id}")
def get_supervisor(supervisor_id: str, db: Session = Depends(get_db)):
    sup = db.get(Supervisor, supervisor_id)
    if not sup:
        raise HTTPException(404)
    return serialize(sup)


@app.post("/api/runs")
async def create_run(body: RunCreate, db: Session = Depends(get_db)):
    sup = db.get(Supervisor, body.supervisor_id)
    if not sup:
        raise HTTPException(404, "Supervisor not found")

    run = Run(
        supervisor_id=body.supervisor_id,
        order_id=body.order_id,
        state={},
        extra_instructions=[],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    workflow_id = f"order-run-{run.id}"
    run.workflow_id = workflow_id
    db.commit()

    await temporal_client.start_workflow(
        "OrderSupervisorWorkflow",
        {
            "run_id": run.id,
            "order_id": body.order_id,
            "supervisor_config": serialize(sup),
        },
        id=workflow_id,
        task_queue="order-supervisor",
    )
    logger.info("Started workflow %s for order %s", workflow_id, body.order_id)
    return serialize(run)


@app.get("/api/runs")
def list_runs(db: Session = Depends(get_db)):
    return [serialize(r) for r in db.query(Run).order_by(Run.created_at.desc()).all()]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)
    return serialize_with_activities(run)


@app.post("/api/runs/{run_id}/events")
async def send_event(run_id: str, body: EventCreate, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)

    activity = Activity(run_id=run_id, type="event", data={"event_type": body.type, **body.data})
    db.add(activity)
    db.commit()

    handle = temporal_client.get_workflow_handle(run.workflow_id)
    await handle.signal("new_event", {"type": body.type, "data": body.data})
    return {"status": "sent"}


@app.post("/api/runs/{run_id}/instructions")
async def add_instruction(run_id: str, body: InstructionCreate, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)

    run.extra_instructions = [*(run.extra_instructions or []), body.instruction]
    activity = Activity(run_id=run_id, type="instruction", data={"instruction": body.instruction})
    db.add(activity)
    db.commit()

    handle = temporal_client.get_workflow_handle(run.workflow_id)
    await handle.signal("add_instruction", body.instruction)
    return {"status": "added"}


@app.post("/api/runs/{run_id}/interrupt")
async def interrupt_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)

    run.status = "paused"
    db.commit()

    handle = temporal_client.get_workflow_handle(run.workflow_id)
    await handle.signal("set_status", "paused")
    return {"status": "paused"}


@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)

    run.status = "active"
    db.commit()

    handle = temporal_client.get_workflow_handle(run.workflow_id)
    await handle.signal("set_status", "active")
    return {"status": "resumed"}


@app.post("/api/runs/{run_id}/terminate")
async def terminate_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404)

    run.status = "terminated"
    run.completed_at = datetime.utcnow()
    db.commit()

    handle = temporal_client.get_workflow_handle(run.workflow_id)
    await handle.signal("set_status", "terminated")
    return {"status": "terminated"}
