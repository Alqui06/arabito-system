from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol = Column(String, default="entrenador")  # "admin", "entrenador", "representante"


class Representante(Base):
    __tablename__ = "representantes"

    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, unique=True, index=True, nullable=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    telefono = Column(String, nullable=False)
    email = Column(String, nullable=True)

    # Relación: Un representante puede tener varios atletas (hijos/representados)
    atletas = relationship("Atleta", back_populates="representante")


class Atleta(Base):
    __tablename__ = "atletas"

    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, nullable=True, index=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    edad = Column(Integer, nullable=True)
    categoria = Column(String, nullable=True)
    posicion = Column(String, nullable=True)
    estatus_solvencia = Column(String, default="Deudor")
    
    # Clave foránea hacia Representante
    representante_id = Column(Integer, ForeignKey("representantes.id"), nullable=True)

    # Relaciones
    representante = relationship("Representante", back_populates="atletas")
    ficha_medica = relationship("FichaMedica", back_populates="atleta", uselist=False, cascade="all, delete-orphan")
    pagos = relationship("Pago", back_populates="atleta", cascade="all, delete-orphan")


class FichaMedica(Base):
    __tablename__ = "fichas_medicas"

    id = Column(Integer, primary_key=True, index=True)
    atleta_id = Column(Integer, ForeignKey("atletas.id"), unique=True)
    grupo_sanguineo = Column(String, nullable=True)
    peso = Column(Float, nullable=True)
    talla = Column(Float, nullable=True)
    alergias = Column(String, nullable=True)
    condiciones_medicas = Column(String, nullable=True)
    contacto_emergencia = Column(String, nullable=True)
    telefono_emergencia = Column(String, nullable=True)

    atleta = relationship("Atleta", back_populates="ficha_medica")


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    atleta_id = Column(Integer, ForeignKey("atletas.id"), nullable=False)
    
    monto = Column(Float, nullable=False)
    fecha_pago = Column(Date, nullable=False)
    concepto = Column(String, nullable=False)
    metodo_pago = Column(String, nullable=False)
    referencia = Column(String, nullable=True)

    atleta = relationship("Atleta", back_populates="pagos")