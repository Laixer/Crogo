import datetime
from typing import Callable
from uuid import UUID
from pydantic import BaseModel, ValidationError

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Depends,
    Security,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import repository, models
from app.config import SettingsLocal
from app.database import SessionLocal

app = FastAPI(docs_url=None, redoc_url=None, root_path="/api")

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChannelMessage(BaseModel):
    type: str
    topic: str | None = None
    data: dict | None = None


class Connection:
    is_claimed: bool = False
    on_signal: list[Callable[[ChannelMessage], None]] = []

    def __init__(self, instance_id: UUID, websocket: WebSocket):
        self.instance_id = instance_id
        self.websocket = websocket


class ConnectionManager:
    connections: list[Connection] = {}

    @property
    def instance_ids(self) -> list[UUID]:
        return [conn.instance_id for conn in self.connections]

    def register_connection(self, connection: Connection):
        self.connections.append(connection)

    def unregister_connection(self, connection: Connection):
        self.connections.remove(connection)

    def register_on_signal(
        self, instance_id: UUID, on_signal: Callable[[ChannelMessage], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.on_signal.append(on_signal)

    def is_claimed(self, instance_id: UUID) -> bool:
        for connection in self.connections:
            if connection.instance_id == instance_id:
                return connection.is_claimed

    def broadcast(self, instance_id: UUID, message: str):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                for signal in connection.on_signal:
                    signal(instance_id, message)


manager = ConnectionManager()


@app.get("/health")
def health() -> dict[str, int]:
    return {"status": 1}


@app.get("/client")
def get_client(request: Request) -> dict[str, str]:
    return {"address": request.client.host}


@app.get("/manifest")
def get_manifest() -> models.Manifest:
    manifest = models.Manifest(
        version="1.0.0",
        repository=[models.ManifestRepository(url="https://edge.laixer.equipment")],
        glonax=models.ManifestGlonax(version="3.5.9"),
    )

    return manifest


@app.get("/instances/live")
def get_client(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> list[UUID]:
    if credentials.credentials != SettingsLocal.security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return manager.instance_ids


# TODO: Not sure if we keep the /app endpoint
@app.websocket("/app/{instance_id}/ws")
async def app_connector(
    instance_id: UUID,
    websocket: WebSocket,
):
    instance_claimed = False

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            try:
                message = ChannelMessage(**data)

                if message.type == "control":
                    if not manager.is_claimed(instance_id) or instance_claimed:
                        # TODO: Send single control message to the instance
                        pass

                elif message.type == "motion":
                    if not manager.is_claimed(instance_id) or instance_claimed:
                        # TODO: Claim the instance
                        pass

            except ValidationError as e:
                message = ChannelMessage(
                    type="error",
                    topic="validation",
                )

                await websocket.send_json(message.model_dump_json())

    except WebSocketDisconnect:
        # TODO: If we claim the instance, we need to release it
        pass


@app.put("/{instance_id}/host", status_code=status.HTTP_201_CREATED)
def put_host(
    host: models.HostConfig,
    instance_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
):
    if credentials.credentials != SettingsLocal.security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    repository.update_host(db, instance_id, host)


@app.get("/{instance_id}/host")
def get_host(
    instance_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> models.HostConfig:
    if credentials.credentials != SettingsLocal.security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return repository.get_host(db, instance_id)


@app.get("/{instance_id}/telemetry")
def get_telemetry(
    instance_id: UUID,
    skip: int = 0,
    limit: int = 5,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> list[models.VMS]:
    if credentials.credentials != SettingsLocal.security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return repository.get_telemetry(db, instance_id, skip, limit)


@app.post("/{instance_id}/telemetry", status_code=status.HTTP_201_CREATED)
def post_telemetry(
    vms: models.VMS,
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

    # probe.instance.id = instance_id
    # probe.meta.remote_address = request.client.host
    repository.create_telemetry(db, instance_id, vms)


# vms_last_update = time.time()


# async def on_signal(instance_id: UUID, message: ChannelMessage):
#     # global vms_last_update

#     await manager.broadcast(instance_id, message.model_dump_json())

# if message.topic == "vms":
#     vms_last_update_elapsed = time.time() - vms_last_update
#     print(f"Elapsed: {vms_last_update_elapsed}")

# if vms_last_update_elapsed > 20:
#     vms = models.VMS(**message.data)
#     repository.create_telemetry(db, instance_id, vms)

# vms_last_update = time.time()


@app.websocket("/{instance_id}/ws")
async def instance_connector(
    instance_id: UUID,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    def on_signal(message: ChannelMessage):
        if message.topic == "vms":
            vms = models.VMS(**message.data)
            # TODO: Check if we need to store the telemetry
            repository.create_telemetry(db, instance_id, vms)
        elif message.topic == "status":
            print(f"Status: {message.data}")
        elif message.topic == "engine":
            print(f"Engine: {message.data}")
        elif message.topic == "error":
            print(f"Error: {message.data}")
        elif message.topic == "boot":
            print(f"Instance {instance_id} booted")

    conn = Connection(instance_id, websocket)
    conn.on_signal.append(on_signal)

    manager.register_connection(conn)

    try:
        while True:
            data = await websocket.receive_json()

            try:
                message = ChannelMessage(**data)

                if message.type == "signal":
                    await manager.broadcast(instance_id, message.model_dump_json())

            except ValidationError as e:
                message = ChannelMessage(
                    type="error",
                    topic="validation",
                )

                await websocket.send_json(message.model_dump_json())

    except WebSocketDisconnect:
        manager.unregister_connection(conn)
