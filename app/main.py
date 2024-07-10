from typing import Callable
from uuid import UUID
from pydantic import ValidationError

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Depends,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import repository, models
from app.routers import user
from app.auth.key import StaticKeyHTTPBearer
from app.config import SettingsLocal
from app.dependencies import get_db

app = FastAPI(docs_url=None, redoc_url=None, root_path="/api")

app.include_router(user.router)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = StaticKeyHTTPBearer(SettingsLocal.security_key)


class Connection:
    is_claimed: bool = False
    on_disconnect: list[Callable[[UUID], None]] = []
    on_message: list[Callable[[models.ChannelMessage], None]] = []

    def __init__(self, instance_id: UUID, websocket: WebSocket):
        self.instance_id = instance_id
        self.websocket = websocket

    async def receive(self) -> models.ChannelMessage:
        try:
            # TODO: Handle json parsing error
            # TODO: iter_json
            data = await self.websocket.receive_json()
            return models.ChannelMessage(**data)
        except ValidationError as e:
            # TODO: Maybe send back websocket error
            print(e)


class MessageRouter:
    connections: list[Connection] = []

    @property
    def instance_ids(self) -> list[UUID]:
        return [conn.instance_id for conn in self.connections]

    def register_connection(self, connection: Connection):
        self.connections.append(connection)

    async def unregister_connection(self, connection: Connection):
        for on_disconnect in connection.on_disconnect:
            await on_disconnect(connection.instance_id)
        connection.on_disconnect.clear()
        connection.on_message.clear()
        self.connections.remove(connection)

    def register_on_message(
        self, instance_id: UUID, on_message: Callable[[models.ChannelMessage], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.on_message.append(on_message)

    def unregister_on_message(
        self, instance_id: UUID, on_message: Callable[[models.ChannelMessage], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                if on_message in connection.on_message:
                    connection.on_message.remove(on_message)

    def register_on_disconnect(
        self, instance_id: UUID, on_disconnect: Callable[[UUID], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                connection.on_disconnect.append(on_disconnect)

    def unregister_on_disconnect(
        self, instance_id: UUID, on_disconnect: Callable[[UUID], None]
    ):
        for connection in self.connections:
            if connection.instance_id == instance_id:
                if on_disconnect in connection.on_disconnect:
                    connection.on_disconnect.remove(on_disconnect)

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
                for on_message in connection.on_message:
                    await on_message(instance_id, message)


manager = MessageRouter()


@app.get("/health")
def health() -> dict[str, int]:
    return {"status": 1}


# TODO; Maybe move
@app.post("/auth/login")
def post_login(user: models.UserLogin):
    if user.email == "henk@kaas.com" and user.password == "ABC@123":
        # TODO: Return a JWT token
        return {"token": "ABC@123"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# TODO: Add an 'is_live' field to /instances
# TAG: App
@app.get("/app/instances/live", dependencies=[Security(security)])
def get_instances_live() -> list[UUID]:
    return manager.instance_ids


# TAG: App
@app.get("/app/instances", dependencies=[Security(security)])
def get_instances(db: Session = Depends(get_db)):
    hosts = repository.get_hosts(db)
    
    for host in hosts:
        if host.instance in manager.instance_ids:
            host.is_live = True

    return hosts


# TAG: App
# TODO: Not sure if we keep the /app endpoint
@app.websocket("/app/{instance_id}/ws")
async def app_connector(
    instance_id: UUID,
    websocket: WebSocket,
):
    instance_claimed = False

    # TODO: Raise exception if instance is not connected
    # TODO: Maybe call close if instance is not connected
    await websocket.accept()

    async def on_output_signal(instance_id: UUID, message: models.ChannelMessage):
        if message.topic == "boot":
            print(f"APP: Instance {instance_id} booted")
        elif message.topic == "error":
            print(f"APP: Error: {message.payload}")
        elif message.topic == "status":
            print(f"APP: Status: {message.payload}")
        elif message.topic == "engine":
            print(f"APP: Engine: {message.payload}")

        await websocket.send_json(message.model_dump())

    async def on_machine_disconnect(instance_id: UUID):
        print(f"APP: Instance {instance_id} disconnected")
        # TODO: Close websocket

    manager.register_on_message(instance_id, on_output_signal)

    # FUTURE: Use context manager for claim/release
    try:
        while True:
            # TODO: Handle non json messages
            data = await websocket.receive_json()

            try:
                message = models.ChannelMessage(**data)

                if message.type == models.ChannelMessageType.COMMAND:
                    if message.topic == "control":
                        print(f"APP: Control: {message.payload}")
                        if not manager.is_claimed(instance_id) or instance_claimed:
                            # manager.claim(instance_id)
                            # instance_claimed = True
                            await manager.command(instance_id, message)

                    elif message.topic == "engine":
                        print(f"APP: Engine: {message.payload}")
                        if not manager.is_claimed(instance_id) or instance_claimed:
                            # manager.claim(instance_id)
                            # instance_claimed = True
                            await manager.command(instance_id, message)

                    elif message.topic == "motion":
                        if not manager.is_claimed(instance_id) or instance_claimed:
                            # manager.claim(instance_id)
                            # instance_claimed = True
                            await manager.command(instance_id, message)

                elif message.type == models.ChannelMessageType.PEER:
                    print(f"APP: Peer sending to machine")
                    await manager.command(instance_id, message)

            except ValidationError as e:
                print(e)

    except WebSocketDisconnect:
        manager.unregister_on_message(instance_id, on_output_signal)
        manager.unregister_on_disconnect(instance_id, on_machine_disconnect)
    finally:
        if instance_claimed:
            manager.release(instance_id)


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

    conn = Connection(instance_id, websocket)

    # TODO: Check if instance is already registered
    manager.register_connection(conn)

    try:
        while True:
            message = await conn.receive()

            if message.type == models.ChannelMessageType.SIGNAL:
                await manager.broadcast(instance_id, message)
            elif message.type == models.ChannelMessageType.PEER:
                await manager.broadcast(instance_id, message)

    except WebSocketDisconnect:
        await manager.unregister_connection(conn)
