from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Atleta(Base):
    __tablename__ = "atletas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    cedula = Column(String, unique=True, index=True, nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    posicion = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    edad = Column(Integer, nullable=True) # ¡Nuevo campo!

    # Relación: Un atleta tiene una (o varias) fichas médicas
    ficha_medica = relationship("FichaMedica", back_populates="atleta", cascade="all, delete-orphan")

class FichaMedica(Base):
    __tablename__ = "fichas_medicas"

    id = Column(Integer, primary_key=True, index=True)
    atleta_id = Column(Integer, ForeignKey("atletas.id"))
    grupo_sanguineo = Column(String, nullable=True)
    alergias = Column(String, nullable=True)
    condiciones_medicas = Column(String, nullable=True)
    contacto_emergencia = Column(String, nullable=True)
    telefono_emergencia = Column(String, nullable=True)

    # Relación inversa
    atleta = relationship("Atleta", back_populates="ficha_medica")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol = Column(String, default="entrenador")