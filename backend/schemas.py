from pydantic import BaseModel
from typing import Optional
from datetime import date

# --- ESQUEMAS DE ATLETAS ---
class AtletaBase(BaseModel):
    nombre: str
    apellido: str
    cedula: str
    fecha_nacimiento: Optional[date] = None
    posicion: Optional[str] = None
    categoria: Optional[str] = None
    edad: Optional[int] = None  # ¡Nuevo campo!

class AtletaCreate(AtletaBase):
    pass

class Atleta(AtletaBase):
    id: int

    class Config:
        from_attributes = True

# --- ESQUEMAS DE FICHAS MÉDICAS ---
class FichaMedicaBase(BaseModel):
    grupo_sanguineo: Optional[str] = None
    alergias: Optional[str] = None
    condiciones_medicas: Optional[str] = None
    contacto_emergencia: Optional[str] = None
    telefono_emergencia: Optional[str] = None

class FichaMedicaCreate(FichaMedicaBase):
    atleta_id: int

class FichaMedica(FichaMedicaBase):
    id: int
    atleta_id: int

    class Config:
        from_attributes = True

# --- ESQUEMAS DE USUARIOS Y AUTENTICACIÓN ---
class UsuarioBase(BaseModel):
    email: str

class UsuarioCreate(UsuarioBase):
    password: str
    rol: Optional[str] = "entrenador"

class Usuario(UsuarioBase):
    id: int
    rol: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None