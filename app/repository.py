from uuid import UUID
from sqlalchemy.orm import Session

from app import schemas, models

# from app.main import Probe, Host


# def get_user(db: Session, user_id: int):
#     return db.query(models.User).filter(models.User.id == user_id).first()


# def get_user_by_email(db: Session, email: str):
#     return db.query(models.User).filter(models.User.email == email).first()


# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.User).offset(skip).limit(limit).all()


# def create_telemetry(db: Session, model: models.Probe):
#     db.add(
#         schemas.Telemetry(
#             instance=model.instance.id,
#             status="HEALTHY",
#             memory=model.host.mem_used / 1_024 / 1_024,
#             swap=model.host.mem_used / 1_024 / 1_024,
#             cpu_1=model.host.cpu1,
#             cpu_5=model.host.cpu5,
#             cpu_15=model.host.cpu15,
#             uptime=model.host.uptime,
#             remote_address=model.meta.remote_address,
#         )
#     )

#     db.commit()


def create_telemetry(db: Session, instance_id: UUID, model: models.VMS):
    db.add(
        schemas.Telemetry(
            instance=instance_id,
            status="HEALTHY",
            memory=model.memory_used / 1_024 / 1_024,
            swap=model.swap_used / 1_024 / 1_024,
            cpu_1=model.cpu_load[0],
            cpu_5=model.cpu_load[1],
            cpu_15=model.cpu_load[2],
            uptime=model.uptime,
            remote_address="127.0.0.2",
        )
    )

    db.commit()


def update_host(db: Session, model: models.Probe):
    db.merge(
        schemas.Host(
            instance=model.instance.id,
            hostname=model.meta.hostname,
            kernel=model.meta.kernel,
            model=model.instance.model,
            serial_number=model.instance.serial_number,
            version=359,
        )
    )

    db.commit()


# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()
