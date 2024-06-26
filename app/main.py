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

from app.database import SessionLocal

security_key = os.environ.get("SECURITY_KEY")
if not security_key:
    raise ValueError("SECURITY_KEY environment variable is not set")

app = FastAPI(docs_url=None, redoc_url=None, root_path="/api")
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# @app.post("/users/", response_model=schemas.User)
# def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return crud.create_user(db=db, user=user)


# TODO: Maybe remove async
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


# TODO: If websocket works, remove this
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


@app.websocket("/app/ws")
async def app_connector(
    websocket: WebSocket,
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            # Depending on the message:
            # - Send a message to a specific instance
            # - Bind the instance connector to the current websocket
            # - Broadcast a message to all instances in a cluster

    except WebSocketDisconnect:
        pass


@app.websocket("/{instance_id}/ws")
async def instance_connector(
    instance_id: UUID,
    websocket: WebSocket,
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Instance {instance_id} says: {data}")

            def request_manifest(instance_id, data):
                pass

            def signal_host(instance_id, data):
                print(data)

            def signal_boot(instance_id, data):
                print(f"Instance {instance_id} booted successfully")

            message_handlers = {
                "req_manifest": request_manifest,
                "sig_host": signal_host,
                "sig_boot": signal_boot,
            }

            message_type = data.get("type")
            handler = message_handlers.get(message_type)
            if handler:
                handler(instance_id, data)
            else:
                # raise ValueError(f"Unknown message type: {message_type}")
                print(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Instance {instance_id} disconnected")
