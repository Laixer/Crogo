from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime

# TODO: use the HttpUrl in model


class VMS(BaseModel):
    memory_used: int  # TODO: Should be a percentage
    memory_total: int  # TODO: Remove this field
    swap_used: int  # TODO: Remove this field
    swap_total: int  # TODO: Remove this field
    cpu_load: tuple[float, float, float]
    uptime: int
    timestamp: datetime  # TODO: Rename to created_at


class Instance(BaseModel):
    id: str
    model: str
    # version: str
    serial_number: str


class HostConfig(BaseModel):
    hostname: str
    kernel: str
    # memory_total: int # TODO: Add this field
    # cpu_count: int # TODO: Add this field
    model: str
    # version: str
    serial_number: str


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
