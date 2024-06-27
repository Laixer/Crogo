import datetime

from pydantic import BaseModel


# TODO: use the HttpUrl in model


class Metadata(BaseModel):
    hostname: str
    kernel: str
    datetime: datetime.datetime
    remote_address: str | None = None


class VMS(BaseModel):
    cpu1: float
    cpu5: float
    cpu15: float
    mem_used: int
    mem_total: int
    uptime: int


class PyVMS(BaseModel):
    memory_used: int
    memory_total: int
    swap_used: int
    swap_total: int
    cpu_load: list[float]
    uptime: int
    timestamp: datetime.datetime


class Instance(BaseModel):
    id: str
    model: str
    # version: str
    serial_number: str


class Probe(BaseModel):
    meta: Metadata
    instance: Instance
    host: VMS | None = None


class Command(BaseModel):
    priority: int
    command: str
    value: str | int | None = None
