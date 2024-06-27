import datetime

from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional
from datetime import datetime

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


class ManifestRepository(BaseModel):
    url: AnyHttpUrl


class ManifestGlonax(BaseModel):
    version: str


class Manifest(BaseModel):
    version: str = Field(description="Manifest version")
    timestamp: datetime.datetime = Field(description="Timestamp in ISO 8601 format")
    repository: list[ManifestRepository] = Field(description="List of repository URLs")
    glonax: ManifestGlonax | None = Field(
        None, description="Glonax-related information"
    )
