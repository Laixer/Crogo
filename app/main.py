from typing import Callable
from uuid import UUID
from pydantic import ValidationError

from fastapi import (
    FastAPI,
    Request,
    Depends,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from app import repository, models
from app.routers import user
from app.auth.key import StaticKeyHTTPBearer
from app.config import SettingsLocal
from app.dependencies import get_db

app = FastAPI(docs_url=None, redoc_url=None, root_path="/api")

app.include_router(user.router)

security = StaticKeyHTTPBearer(SettingsLocal.security_key)


class Connection:
    is_claimed: bool = False
    on_disconnect: list[Callable[[UUID], None]] = []
    on_signal: list[Callable[[models.ChannelMessage], None]] = []

    def __init__(self, instance_id: UUID, websocket: WebSocket):
        self.instance_id = instance_id
        self.websocket = websocket


class MessageRouter:
    connections: list[Connection] = []

    @property
    def instance_ids(self) -> list[UUID]:
        return [conn.instance_id for conn in self.connections]

    def register_connection(self, connection: Connection):
        self.connections.append(connection)

    async def unregister_connection(self, connection: Connection):
        for callable in connection.on_disconnect:
            await callable(connection.instance_id)
        self.connections.remove(connection)

    def register_on_signal(
        self, instance_id: UUID, on_signal: Callable[[models.ChannelMessage], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.on_signal.append(on_signal)

    def unregister_on_signal(
        self, instance_id: UUID, on_signal: Callable[[models.ChannelMessage], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.on_signal.remove(on_signal)

    def is_claimed(self, instance_id: UUID) -> bool:
        for connection in self.connections:
            if connection.instance_id == instance_id:
                return connection.is_claimed

    def claim(self, instance_id: UUID):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.is_claimed = True

    def release(self, instance_id: UUID):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.is_claimed = False

    async def command(self, instance_id: UUID, message: models.ChannelMessage):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                if connection.is_claimed:
                    raise Exception("Instance is claimed")
                await connection.websocket.send_json(message.model_dump())

    async def broadcast(self, instance_id: UUID, message: models.ChannelMessage):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                for signal in connection.on_signal:
                    await signal(instance_id, message)


manager = MessageRouter()


@app.get("/health")
def health() -> dict[str, int]:
    return {"status": 1}


# TODO: Get from database
@app.get("/manifest")
def get_manifest() -> models.Manifest:
    manifest = models.Manifest(
        version="1.0.0",
        repository=[models.ManifestRepository(url="https://edge.laixer.equipment")],
        glonax=models.ManifestGlonax(version="3.5.9"),
    )

    return manifest


# TODO: Add an 'is_live' field to /instances
# TAG: App
@app.get("/instances/live", dependencies=[Security(security)])
def get_instances_live() -> list[UUID]:
    return manager.instance_ids


# TODO: Add Control message
# @app.post("/{instance_id}/control", dependencies=[Security(security)])
# def post_command(instance_id: UUID, command: models.Command):
#     message = models.ChannelMessage(
#         type="control",
#         topic="command",
#         data=command.dict(),
#     )
#
#     manager.command(instance_id, message)

# TODO: Add Engine message
# @app.post("/{instance_id}/engine", dependencies=[Security(security)])
# def post_engine(instance_id: UUID, engine: models.Engine):
#     message = models.ChannelMessage(
#         type="control",
#         topic="engine",
#         data=engine.dict(),
#     )

#     manager.command(instance_id, message)


# TAG: App
# TODO: Not sure if we keep the /app endpoint
@app.websocket("/app/{instance_id}/ws")
async def app_connector(
    instance_id: UUID,
    websocket: WebSocket,
):
    instance_claimed = False

    await websocket.accept()

    async def on_machine_signal(instance_id: UUID, message: models.ChannelMessage):
        if message.topic == "boot":
            print(f"APP: Instance {instance_id} booted")
        elif message.topic == "error":
            print(f"APP: Error: {message.data}")
        elif message.topic == "status":
            print(f"APP: Status: {message.data}")
        elif message.topic == "engine":
            print(f"APP: Engine: {message.data}")

        await websocket.send_json(message.model_dump())

    manager.register_on_signal(instance_id, on_machine_signal)

    # FUTURE: Use context manager for claim/release
    try:
        while True:
            # TODO: Handle non json messages
            data = await websocket.receive_json()

            try:
                message = models.ChannelMessage(**data)

                if message.type == "control":
                    print(f"APP: Control: {message.data}")
                    if not manager.is_claimed(instance_id) or instance_claimed:
                        # TODO: Send single control message to the instance
                        await manager.command(instance_id, message)

                elif message.type == "motion":
                    if not manager.is_claimed(instance_id) or instance_claimed:
                        manager.claim(instance_id)
                        instance_claimed = True

            except ValidationError as e:
                message = models.ChannelMessage(
                    type="error",
                    topic="validation",
                )

                await websocket.send_json(message.model_dump_json())

    except WebSocketDisconnect:
        manager.unregister_on_signal(instance_id, on_machine_signal)
    finally:
        if instance_claimed:
            manager.release(instance_id)


# TAG: Machine
@app.post("/{instance_id}/enroll")
def post_enroll():
    # TODO: Add instance to auth (inactive) repository and return the token
    return {"token": SettingsLocal.security_key}


# TAG: Machine
@app.put(
    "/{instance_id}/host",
    status_code=201,
    dependencies=[Security(security)],
)
def put_host(
    host: models.HostConfig,
    instance_id: UUID,
    db: Session = Depends(get_db),
):
    repository.update_host(db, instance_id, host)


# FUTURE: Maybe removed the 'instance' path
# TAG: Machine
@app.post(
    "/{instance_id}/telemetry",
    status_code=201,
    dependencies=[Security(security)],
)
def post_telemetry(
    telemetry: models.Telemetry,
    instance_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    telemetry.remote_address = request.client.host
    repository.create_telemetry(db, instance_id, telemetry)
    # TODO: Update last contact with the instance


# TAG: Machine
@app.websocket("/{instance_id}/ws")
async def instance_connector(
    instance_id: UUID,
    websocket: WebSocket,
):
    await websocket.accept()

    async def on_signal(instance_id: UUID, message: models.ChannelMessage):
        if message.topic == "boot":
            print(f"MACHINE: Instance {instance_id} booted")
        elif message.topic == "error":
            print(f"MACHINE: Error: {message.data}")
        elif message.topic == "status":
            print(f"MACHINE: Status: {message.data}")
        elif message.topic == "engine":
            print(f"MACHINE: Engine: {message.data}")

    conn = Connection(instance_id, websocket)
    conn.on_signal.append(on_signal)  # TODO: Dont need this no more

    manager.register_connection(conn)

    try:
        while True:
            # TODO: Handle non json messages
            data = await websocket.receive_json()

            try:
                message = models.ChannelMessage(**data)

                if message.type == "signal":
                    await manager.broadcast(instance_id, message)

            except ValidationError as e:
                message = models.ChannelMessage(
                    type="error",
                    topic="validation",
                )

                await websocket.send_json(message.model_dump())

    except WebSocketDisconnect:
        await manager.unregister_connection(conn)
