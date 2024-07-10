from uuid import UUID
from sqlalchemy.orm import Session

from app import schemas, models


def get_hosts(db: Session) -> list[models.HostConfig]:
    hosts = db.query(schemas.Host).all()

    return [
        models.HostConfig(
            instance=host.instance,
            name=host.name,
            hostname=host.hostname,
            kernel=host.kernel,
            memory_total=0,
            cpu_count=0,
            model=host.model,
            serial_number=host.serial_number,
            version=host.version,
        )
        for host in hosts
    ]


def get_host(db: Session, instance_id: UUID) -> models.HostConfig:
    host = db.query(schemas.Host).filter(schemas.Host.instance == instance_id).first()

    return models.HostConfig(
        name=host.name,
        hostname=host.hostname,
        kernel=host.kernel,
        model=host.model,
        serial_number=host.serial_number,
        version=host.version,
    )


def update_host(db: Session, instance_id: UUID, model: models.HostConfig):
    db.merge(
        schemas.Host(
            instance=instance_id,
            name=model.name,
            hostname=model.hostname,
            kernel=model.kernel,
            model=model.model,
            serial_number=model.serial_number,
            version=model.version,
        )
    )

    db.commit()


def get_telemetry(
    db: Session, instance_id: UUID, offset: int = 0, limit: int = 5
) -> list[models.Telemetry]:
    telemetry = (
        db.query(schemas.Telemetry)
        .filter(schemas.Telemetry.instance == instance_id)
        .order_by(schemas.Telemetry.created_at.desc())
        .offset(offset)
        .limit(min(limit, 50))
        .all()
    )

    return [
        models.Telemetry(
            memory_used=telemetry.memory_used,
            disk_used=telemetry.disk_used,
            cpu_freq=telemetry.cpu_freq,
            cpu_load=[telemetry.cpu_1, telemetry.cpu_5, telemetry.cpu_15],
            uptime=telemetry.uptime,
            created_at=telemetry.created_at,
        )
        for telemetry in telemetry
    ]


def create_telemetry(db: Session, instance_id: UUID, model: models.Telemetry):
    db.add(
        schemas.Telemetry(
            instance=instance_id,
            memory_used=model.memory_used,
            disk_used=model.disk_used,
            cpu_freq=model.cpu_freq,
            cpu_1=model.cpu_load[0],
            cpu_5=model.cpu_load[1],
            cpu_15=model.cpu_load[2],
            uptime=model.uptime,
            remote_address=model.remote_address,
        )
    )

    db.commit()
