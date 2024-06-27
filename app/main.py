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
