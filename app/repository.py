from uuid import UUID
from sqlalchemy.orm import Session

from app import schemas, models


def get_hosts(db: Session) -> list[models.HostConfig]:
    hosts = db.query(schemas.Host).all()

    return [
        models.HostConfig(
            hostname=host.hostname,
            kernel=host.kernel,
            model=host.model,
            serial_number=host.serial_number,
        )
        for host in hosts
    ]


def get_host(db: Session, instance_id: UUID) -> models.HostConfig:
    host = db.query(schemas.Host).filter(schemas.Host.instance == instance_id).first()

    return models.HostConfig(
        hostname=host.hostname,
        kernel=host.kernel,
        model=host.model,
        serial_number=host.serial_number,
    )


def update_host(db: Session, instance_id: UUID, model: models.HostConfig):
    db.merge(
        schemas.Host(
            instance=instance_id,
            hostname=model.hostname,
            kernel=model.kernel,
            model=model.model,
            serial_number=model.serial_number,
            version=359,
        )
    )

    db.commit()


def get_telemetry(
    db: Session, instance_id: UUID, offset: int = 0, limit: int = 5
) -> list[models.VMS]:
    telemetry = (
        db.query(schemas.Telemetry)
        .filter(schemas.Telemetry.instance == instance_id)
        .order_by(schemas.Telemetry.created_at.desc())
        .offset(offset)
        .limit(min(limit, 50))
        .all()
    )

    return [
        models.VMS(
            memory_used=telemetry.memory * 1_024 * 1_024,
            memory_total=0,
            swap_used=telemetry.swap * 1_024 * 1_024,
            swap_total=0,
            cpu_load=[telemetry.cpu_1, telemetry.cpu_5, telemetry.cpu_15],
            uptime=telemetry.uptime,
            timestamp=telemetry.created_at,
        )
        for telemetry in telemetry
    ]


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
