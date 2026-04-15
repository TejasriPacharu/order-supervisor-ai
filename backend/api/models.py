import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


def new_id():
    return str(uuid.uuid4())


class Supervisor(Base):
    __tablename__ = "supervisors"
    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    base_instruction = Column(Text, nullable=False)
    actions = Column(JSON, default=list)
    wake_behavior = Column(String, default="normal")
    model = Column(String, default="claude-sonnet-4-20250514")
    wake_aggressiveness = Column(String, default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)
    runs = relationship("Run", back_populates="supervisor")


class Run(Base):
    __tablename__ = "runs"
    id = Column(String, primary_key=True, default=new_id)
    supervisor_id = Column(String, ForeignKey("supervisors.id"), nullable=False)
    order_id = Column(String, nullable=False)
    status = Column(String, default="active")
    state = Column(JSON, default=dict)
    workflow_id = Column(String)
    extra_instructions = Column(JSON, default=list)
    final_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    supervisor = relationship("Supervisor", back_populates="runs")
    activities = relationship("Activity", back_populates="run", order_by="Activity.created_at")


class Activity(Base):
    __tablename__ = "activities"
    id = Column(String, primary_key=True, default=new_id)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    type = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("Run", back_populates="activities")
