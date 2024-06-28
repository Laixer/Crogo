from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime

# TODO: use the HttpUrl in model


class Metadata(BaseModel):
    hostname: str
    kernel: str
    datetime: datetime
    remote_address: str | None = None
    # memory_total: int
    # cpu_count: int


# class VMS(BaseModel):
#     cpu1: float
#     cpu5: float
#     cpu15: float
#     mem_used: int
#     mem_total: int
#     uptime: int


class VMS(BaseModel):
    memory_used: int
    memory_total: int # TODO: Remove this field
    swap_used: int # TODO: Remove this field
    swap_total: int # TODO: Remove this field
    cpu_load: list[float]
    uptime: int
    timestamp: datetime


class Instance(BaseModel):
    id: str
    model: str
    # version: str
    serial_number: str


class HostConfig(BaseModel):
    meta: Metadata
    instance: Instance
    # host: VMS | None = None


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
    timestamp: datetime = Field(description="Timestamp in ISO 8601 format")
    repository: list[ManifestRepository] = Field(description="List of repository URLs")
    glonax: ManifestGlonax | None = Field(
        None, description="Glonax-related information"
    )
