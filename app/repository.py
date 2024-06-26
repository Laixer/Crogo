from sqlalchemy.orm import Session

from app import schemas
from app.main import Probe, Host


# def get_user(db: Session, user_id: int):
#     return db.query(models.User).filter(models.User.id == user_id).first()


# def get_user_by_email(db: Session, email: str):
#     return db.query(models.User).filter(models.User.email == email).first()


# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.User).offset(skip).limit(limit).all()


def create_telemetry(db: Session, model: Probe):
    # TODO: Remove version from Probe
    db.add(
        schemas.Probe(
            instance=model.instance.id,
            status="HEALTHY",
            version=359,  # TODO: Remove version from Probe
            memory=model.host.mem_used / 1_024 / 1_024,
            swap=model.host.mem_used / 1_024 / 1_024,
            cpu_1=model.host.cpu1,
            cpu_5=model.host.cpu5,
            cpu_15=model.host.cpu15,
            uptime=model.host.uptime,
        )
    )

    # TODO: Move remote_address to Probe
    db.merge(
        schemas.Host(
            instance=model.instance.id,
            hostname=model.meta.hostname,
            kernel=model.meta.kernel,
            model=model.instance.model,
            serial_number=model.instance.serial_number,
            version=359,
            # remote_address=request.client.host,
        )
    )

    db.commit()


# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()


# def create_user_item(db: Session, item: ItemCreate, user_id: int):
#     db_item = models.Item(item.model_dump(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item
