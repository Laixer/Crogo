from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Security

from sqlalchemy.orm import Session

from app import models, repository
from app.auth.key import StaticKeyHTTPBearer
from app.dependencies import get_db

router = APIRouter()

test_key = "ABC@123"
security = StaticKeyHTTPBearer(test_key)


@router.post("/login", tags=["app"])
def post_login(user: models.UserLogin):
    if user.email == "test@example.com" and user.password == "password":
        # TODO: Return a JWT token
        return {"token": test_key}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/instances", dependencies=[Security(security)], tags=["app"])
def get_instances(db: Session = Depends(get_db)):
    return repository.get_hosts(db)


# TODO: Maybe removed the 'host' path
# TAG: App
@router.get("/{instance_id}/host", dependencies=[Security(security)])
def get_host(
    instance_id: UUID,
    db: Session = Depends(get_db),
) -> models.HostConfig:
    return repository.get_host(db, instance_id)


# TAG: App
@router.get("/{instance_id}/telemetry", dependencies=[Security(security)])
def get_telemetry(
    instance_id: UUID,
    skip: int = 0,
    limit: int = 5,
    db: Session = Depends(get_db),
) -> list[models.Telemetry]:
    return repository.get_telemetry(db, instance_id, skip, limit)
