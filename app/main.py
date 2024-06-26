import os
import datetime
from typing import Union
from uuid import UUID
from pydantic import BaseModel

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Header,
    Depends,
    Security,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_key = os.environ.get("SECURITY_KEY")
if not security_key:
    raise ValueError("SECURITY_KEY environment variable is not set")

app = FastAPI(docs_url=None, redoc_url=None)  # root_path="/api"
security = HTTPBearer()


# TODO: use the HttpUrl in model


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
    value: str | int | None = None


@app.get("/client")
def get_client(request: Request):
    return {"address": request.client.host, "port": request.client.port}


@app.get("/{instance_id}/manifest")
async def fetch_manifest(
    instance_id: UUID,
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


@app.post("/{instance_id}/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(
    probe: Probe,
    instance_id: UUID,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    if credentials.credentials != security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # TODO: HACK, FIX THIS
    from sqlalchemy.orm import Session
    from .database import engine
    from .schemas import Probe, Host

    with Session(engine) as session:
        # TODO: Remove version from Probe
        session.add(
            Probe(
                instance=instance_id,
                status="HEALTHY",
                version=359,  # TODO: Remove version from Probe
                memory=probe.host.mem_used / 1_024 / 1_024,
                swap=probe.host.mem_used / 1_024 / 1_024,
                cpu_1=probe.host.cpu1,
                cpu_5=probe.host.cpu5,
                cpu_15=probe.host.cpu15,
                uptime=probe.host.uptime,
            )
        )

        # TODO: Move remote_address to Probe
        session.merge(
            Host(
                instance=instance_id,
                hostname=probe.meta.hostname,
                kernel=probe.meta.kernel,
                model=probe.instance.model,
                serial_number=probe.instance.serial_number,
                version=359,
                remote_address=request.client.host,
            )
        )

        session.commit()

    # print(probe)


@app.get("/{instance_id}/command")
async def fetch_command(
    instance_id: UUID,
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


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/{instance_id}/ws")
async def websocket_endpoint(
    instance_id: UUID,
    websocket: WebSocket,
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Instance {instance_id} says: {data}")

            # { "type": "signal", ... }
            # { "type": "req_manifest", "status": "shipped", ... }
            # { "type": "error", "code": 404, "message": "Not found" }

            def request_manifest(data):
                pass

            def signal_host(data):
                print(data)

            message_handlers = {
                "req_manifest": request_manifest,
                "sig_host": signal_host,
            }

            message_type = data.get("type")
            handler = message_handlers.get(message_type)
            if handler:
                handler(data)
            else:
                raise ValueError(f"Unknown message type: {message_type}")

            # try:
            #     if message_type == "signal":
            #         handle_new_order(data)
            #     elif message_type == "update_status":
            #         handle_update_status(data)
            #     elif message_type == "error":
            #         handle_error(data)
            #     else:
            #         raise ValueError(f"Unknown message type: {message_type}")
            # except:
            #     # Handle parsing errors or missing message types
            #     # log_error(f"Error processing message: {e}")
            #     pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Instance {instance_id} disconnected")
