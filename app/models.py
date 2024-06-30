from pydantic import BaseModel, EmailStr, Field, HttpUrl
from datetime import datetime


class VMS(BaseModel):
    memory_used: int  # TODO: Should be a percentage
    memory_total: int  # TODO: Remove this field
    swap_used: int  # TODO: Remove this field
    swap_total: int  # TODO: Remove this field
    cpu_load: tuple[float, float, float]
    uptime: int = Field(..., description="Uptime in seconds")
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


class UserLogin(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)


class ManifestRepository(BaseModel):
    url: HttpUrl


class ManifestGlonax(BaseModel):
    version: str


class Manifest(BaseModel):
    version: str = Field(description="Manifest version")
    repository: list[ManifestRepository] = Field(description="List of repository URLs")
    glonax: ManifestGlonax | None = Field(
        None, description="Glonax-related information"
    )
