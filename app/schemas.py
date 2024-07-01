import uuid

from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    Numeric,
    UniqueConstraint,
)


Base = declarative_base()


class Auth(Base):
    __tablename__ = "auth"

    token = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Auth(token='{self.token}', is_active='{self.is_active}')>"


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (UniqueConstraint("instance", "created_at"),)

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    instance = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    remote_address = Column(String)
    # location = Column(POINT)
    altitude = Column(Float)
    speed = Column(Float)
    satellites = Column(Integer)
    memory_used = Column(Numeric)
    disk_used = Column(Numeric)
    cpu_freq = Column(Float)
    cpu_1 = Column(Float)
    cpu_5 = Column(Float)
    cpu_15 = Column(Float)
    uptime = Column(Integer)
    rpm = Column(Integer)

    def __repr__(self):
        return f"<Telemetry(instance='{self.instance}', created_at='{self.created_at}')>"


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
