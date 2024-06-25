import os
import datetime
from typing import Union
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Request, Header, Depends, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_key = os.environ.get("SECURITY_KEY")
if not security_key:
    raise ValueError("SECURITY_KEY environment variable is not set")

app = FastAPI(docs_url=None, redoc_url=None)  # root_path="/api"
security = HTTPBearer()


class Metadata(BaseModel):
    hostname: str
    kernel: str
    datetime: datetime.datetime


class VMS(BaseModel):
    cpu1: float
    cpu5: float
    cpu15: float
    mem_used: int
    mem_total: int
    uptime: int


class Instance(BaseModel):
    id: str
    model: str
    # version: str
    serial_number: str


class Probe(BaseModel):
    meta: Metadata
    instance: Instance
    host: Union[VMS, None] = None


class Command(BaseModel):
    priority: int
    command: str
    value: Union[str, int, None] = None


@app.get("/client")
def get_client(request: Request):
    return {"address": request.client.host, "port": request.client.port}


@app.get("/{instance_id}/manifest")
async def fetch_manifest(
    instance_id: str,
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    if credentials.credentials != security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return {
        "version": "1.0.0",
        "timestamp": "2024-06-25T16:38:44+0000",
        "repository": [
            "https://edge1.example.com",
        ],
        "cluster": {
            "name": "cluster-1",
            "id": "1b9b3603-e5da-42cf-ae14-f74bf0391b96",
            "nodes": [
                ("instance-1", instance_id),
            ],
        },
        "instance": {"name": "instance-1", "id": instance_id},
        "glonax": {
            "version": "3.5.9",
        },
    }


@app.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(
    probe: Probe,
    x_instance_id: str = Header(),
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    if credentials.credentials != security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # print(probe)
    # print(x_instance_id)


@app.get("/command")
async def fetch_command(
    x_instance_id: str = Header(),
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    if credentials.credentials != security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return [
        Command(priority=1, command="reboot"),
        Command(priority=2, command="engine_start", value=950),
    ]
