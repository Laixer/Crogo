import uuid

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint


Base = declarative_base()


class Probe(Base):
    __tablename__ = "probe"
    __table_args__ = (UniqueConstraint("instance", "created_at"),)

    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), primary_key=True
    )
    instance = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    status = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
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
    hostname = Column(String)
    kernel = Column(String)
    model = Column(String)
    serial_number = Column(String)
    version = Column(Integer, nullable=False)
    remote_address = Column(String)

    def __repr__(self):
        return f"<Host(instance={self.instance}, hostname='{self.hostname}')>"
