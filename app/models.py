from uuid import UUID
from enum import Enum, IntEnum
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from datetime import datetime


class ChannelMessageType(str, Enum):
    COMMAND = "command"
    SIGNAL = "signal"
    CONTROL = "control"
    PEER = "peer"
    ERROR = "error"


class ChannelMessage(BaseModel):
    type: ChannelMessageType
    topic: str
    payload: dict | None = None


# NOTE: Glonax model
class ControlType(IntEnum):
    ENGINE_REQUEST = 0x01
    ENGINE_SHUTDOWN = 0x02
    HYDRAULIC_QUICK_DISCONNECT = 0x5
    HYDRAULIC_LOCK = 0x6
    MACHINE_SHUTDOWN = 0x1B
    MACHINE_ILLUMINATION = 0x1C
    MACHINE_LIGHTS = 0x2D
    MACHINE_HORN = 0x1E


# NOTE: Glonax model
class Control(BaseModel):
    type: ControlType
    value: bool

    def to_bytes(self):
        return bytes([self.type.value, self.value])

    def from_bytes(data):
        type = ControlType(data[0])
        value = bool(data[1])

        return Control(type=type, value=value)


class Telemetry(BaseModel):
    memory_used: float
    disk_used: float
    cpu_freq: float
    cpu_load: tuple[float, float, float]
    uptime: int = Field(..., description="Uptime in seconds")
    created_at: datetime | None = None
    remote_address: str | None = None


class HostConfig(BaseModel):
    # instance: UUID # TODO: Add this field
    name: str | None = None
    hostname: str
    kernel: str
    memory_total: int
    cpu_count: int
    model: str
    version: str
    serial_number: str


class MacheinEnrollment(BaseModel):
    instance: UUID


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
