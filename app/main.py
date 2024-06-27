import os
import time
import datetime
from typing import Union
from uuid import UUID
from pydantic import BaseModel, ValidationError

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
from sqlalchemy.orm import Session

from app import repository, models, schemas
from app.config import SettingsLocal
from app.database import SessionLocal
from app.models import Probe, Command

app = FastAPI(docs_url=None, redoc_url=None, root_path="/api")
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, int]:
    return {"status": 1}


@app.get("/client")
def get_client(request: Request) -> dict[str, str]:
    return {"address": request.client.host}


# TODO: Turn manifest into a Pydantic model
@app.get("/manifest")
def fetch_manifest():
    return {
        "version": "1.0.0",
        "timestamp": "2024-06-25T16:38:44+0000",
        "repository": [
            "https://edge.laixer.equipment",
        ],
        "glonax": {
            "version": "3.5.9",
        },
    }


# TODO: Replace the telemetry model with the PyVMS model
@app.post("/{instance_id}/telemetry", status_code=status.HTTP_201_CREATED)
def post_telemetry(
    probe: Probe,
    instance_id: UUID,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
):
    if credentials.credentials != SettingsLocal.security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    probe.instance.id = instance_id
    probe.meta.remote_address = request.client.host
    repository.update_host(db, probe)
    repository.create_telemetry(db, probe)


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
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            print(data)

            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Instance {instance_id} says: {data}")

            # Depending on the message:
            # - Send a message to a specific instance
            # - Bind the instance connector to the current websocket
            # - Broadcast a message to all instances in a cluster

    except WebSocketDisconnect:
        manager.disconnect(websocket)


class PyVMS(BaseModel):
    memory_used: int
    memory_total: int
    swap_used: int
    swap_total: int
    cpu_load: list[float]
    uptime: int
    timestamp: datetime.datetime


class ChannelMessage(BaseModel):
    type: str
    topic: str | None = None
    data: dict | None = None


vms_last_update = time.time()


@app.websocket("/{instance_id}/ws")
async def instance_connector(
    instance_id: UUID,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            async def on_signal(instance_id: UUID, message: ChannelMessage):
                global vms_last_update

                await manager.broadcast(message.model_dump_json())

                if message.topic == "vms":
                    vms_last_update_elapsed = time.time() - vms_last_update
                    print(f"Elapsed: {vms_last_update_elapsed}")

                    if vms_last_update_elapsed > 20:
                        vms = PyVMS(**message.data)

                        print(vms)

                        db.add(
                            schemas.Telemetry(
                                instance=instance_id,
                                status="HEALTHY",
                                memory=vms.memory_used / 1_024 / 1_024,
                                swap=vms.swap_used / 1_024 / 1_024,
                                cpu_1=vms.cpu_load[0],
                                cpu_5=vms.cpu_load[1],
                                cpu_15=vms.cpu_load[2],
                                uptime=vms.uptime,
                                remote_address="127.0.0.2",
                            )
                        )

                        db.commit()
                        vms_last_update = time.time()
                elif message.topic == "status":
                    print(f"Status: {message.data}")
                elif message.topic == "engine":
                    print(f"Engine: {message.data}")

            def on_notify(instance_id: UUID, message: ChannelMessage):
                if message.topic == "boot":
                    print(f"Notify: instance {instance_id} successfully booted")

            try:
                message = ChannelMessage(**data)

                if message.type == "signal":
                    await on_signal(instance_id, message)
                elif message.type == "notify":
                    on_notify(instance_id, message)

            except ValidationError as e:
                message = ChannelMessage(
                    type="error",
                    topic="validation",
                )

                await websocket.send_json(message.model_dump_json())

    except WebSocketDisconnect:
        # manager.disconnect(websocket)
        pass
        # await manager.broadcast(f"Instance {instance_id} disconnected")
