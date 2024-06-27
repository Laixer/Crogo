import uuid

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint


Base = declarative_base()


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (UniqueConstraint("instance", "created_at"),)

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    instance = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    status = Column(String, nullable=False)
    remote_address = Column(String)
    # location = Column(POINT)
    altitude = Column(Float)
    speed = Column(Float)
    satellites = Column(Integer)
    memory = Column(Integer)
    swap = Column(Integer)
    cpu_1 = Column(Float)
    cpu_5 = Column(Float)
    cpu_15 = Column(Float)
    uptime = Column(Integer)
    rpm = Column(Integer)

    def __repr__(self):
        return f"<Probe(instance='{self.instance}', created_at='{self.created_at}', status='{self.status}')>"


class Host(Base):
    __tablename__ = "host"

    instance = Column(UUID(as_uuid=True), primary_key=True)
    hostname = Column(String)  # TODO: should be not null
    kernel = Column(String)  # TODO: should be not null
    model = Column(String)  # TODO: should be not null
    serial_number = Column(String)  # TODO: should be unique, not null
    version = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Host(instance={self.instance}, hostname='{self.hostname}')>"
