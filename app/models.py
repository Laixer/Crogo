from pydantic import BaseModel, EmailStr, Field, HttpUrl
from datetime import datetime


class Telemetry(BaseModel):
    memory_used: float
    disk_used: float
    cpu_freq: float
    cpu_load: tuple[float, float, float]
    uptime: int = Field(..., description="Uptime in seconds")
    created_at: datetime | None = None


class HostConfig(BaseModel):
    # instance: UUID # TODO: Add this field
    # name: str # TODO: Add this field
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
