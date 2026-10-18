from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


def iniciar_base_datos(database_url: str):
    motor = create_engine(database_url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(motor)
    except Exception:
        motor.dispose()
        raise
    return motor, sessionmaker(bind=motor, expire_on_commit=False)
