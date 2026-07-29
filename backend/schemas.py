from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional, List


# ==================== USUARIOS / AUTENTICACIÓN ====================

class UsuarioBase(BaseModel):
    email: EmailStr
    rol: Optional[str] = "entrenador"


class UsuarioCreate(UsuarioBase):
    password: str


class Usuario(UsuarioBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


# ==================== ATLETAS ====================
# ==================== REPRESENTANTES ====================

class RepresentanteResumen(BaseModel):
    id: int
    nombre: str
    apellido: Optional[str] = None
    cedula: Optional[str] = None
    telefono: Optional[str] = None

    class Config:
        from_attributes = True

class AtletaBase(BaseModel):
    cedula: Optional[str] = None
    nombre: str
    apellido: str
    fecha_nacimiento: Optional[date] = None
    representante: Optional[str] = None
    nombre_representante: Optional[str] = None
    telefono_representante: Optional[str] = None
    estatus_solvencia: Optional[str] = "Deudor"


class AtletaCreate(AtletaBase):
    pass


class Atleta(AtletaBase):
    id: int
    edad: Optional[int] = None
    categoria: Optional[str] = None

    class Config:
        from_attributes = True



# ==================== FICHAS MÉDICAS ====================

class AtletaResumen(BaseModel):
    id: int
    nombre: str
    apellido: str

    class Config:
        from_attributes = True


class FichaMedicaBase(BaseModel):
    atleta_id: int
    grupo_sanguineo: Optional[str] = None
    peso: Optional[float] = None
    talla: Optional[float] = None
    alergias: Optional[str] = None
    condiciones_medicas: Optional[str] = None
    contacto_emergencia: Optional[str] = None
    telefono_emergencia: Optional[str] = None


class FichaMedicaCreate(FichaMedicaBase):
    pass


class FichaMedica(FichaMedicaBase):
    id: int
    atleta: Optional[AtletaResumen] = None  # Carga automática de nombre y apellido

    class Config:
        from_attributes = True

# ==================== PAGOS Y FINANZAS ====================

class PagoBase(BaseModel):
    atleta_id: int
    monto: float
    concepto: Optional[str] = "Mensualidad"
    metodo_pago: str
    referencia: Optional[str] = None


class PagoCreate(PagoBase):
    pass


class Pago(PagoBase):
    id: int
    fecha_pago: datetime

    class Config:
        from_attributes = True


# ==================== SCHEMAS DE REPORTES ====================

class ResumenSolvencia(BaseModel):
    total_atletas: int
    total_solventes: int
    total_deudores: int
    porcentaje_solvencia: float


class ResumenFinanciero(BaseModel):
    total_recaudado: float
    total_transacciones: int

