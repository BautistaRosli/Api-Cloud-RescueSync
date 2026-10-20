from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.seed import poblar_base_datos


def iniciar_base_datos(database_url: str, ejecutar_seed: bool = True):
    motor = create_engine(database_url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(motor)

        if ejecutar_seed:
            sesion_factory = sessionmaker(bind=motor, expire_on_commit=False)
            db = sesion_factory()
            try:
                resultado = poblar_base_datos(db)
                print(f"[SEED] Base de datos poblada: {resultado}")
            finally:
                db.close()
    except Exception:
        motor.dispose()
        raise
    return motor, sessionmaker(bind=motor, expire_on_commit=False)