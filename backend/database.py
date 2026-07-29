from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de la base de datos SQLite (se creará un archivo llamado arabito.db en la raíz)
SQLALCHEMY_DATABASE_URL = "sqlite:///./arabito.db"

# Crear el motor de la base de datos
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Crear una clase de sesión para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para crear los modelos
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos en nuestras rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()