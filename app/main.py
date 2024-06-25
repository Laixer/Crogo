import os
import datetime
from typing import Union
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Request, Header, Depends, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_key = os.environ.get("SECURITY_KEY")
if not security_key:
    raise ValueError("SECURITY_KEY environment variable is not set")

app = FastAPI(docs_url=None, redoc_url=None)
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


@app.get("/client")
def get_client(request: Request):
    return {"address": request.client.host, "port": request.client.port}


@app.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(
    probe: Probe,
    x_instance_id: str = Header(),
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    # print(probe)
    # print(x_instance_id)
    pass


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

    return [{"command": "ls"}]
