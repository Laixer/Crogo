from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Security

from sqlalchemy.orm import Session

from app import models, repository
from app.auth.key import StaticKeyHTTPBearer
from app.dependencies import get_db

test_key = "ABC@123"
security = StaticKeyHTTPBearer(test_key)

router = APIRouter(
    prefix="/app",
    tags=["app"],
    dependencies=[Security(security)],
)


# TODO; Maybe move
@router.post("/login", tags=["app"])
def post_login(user: models.UserLogin):
    if user.email == "test@example.com" and user.password == "password":
        # TODO: Return a JWT token
        return {"token": test_key}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/instances")
def get_instances(db: Session = Depends(get_db)):
    return repository.get_hosts(db)


# TODO: Maybe removed the 'host' path
@router.get("/{instance_id}/host")
def get_host(
    instance_id: UUID,
    db: Session = Depends(get_db),
) -> models.HostConfig:
    return repository.get_host(db, instance_id)


@router.get("/{instance_id}/telemetry")
def get_telemetry(
    instance_id: UUID,
    skip: int = 0,
    limit: int = 5,
    db: Session = Depends(get_db),
) -> list[models.Telemetry]:
    return repository.get_telemetry(db, instance_id, skip, limit)
