from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Importaciones locales
import models
from database import get_db

# Configuración de Clave Secreta y Algoritmo para JWT
SECRET_KEY = "arabito_fc_secret_key_super_segura_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Duración del token: 24 horas

# Configuración de PassLib con Bcrypt para el hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad OAuth2 utilizando el endpoint /token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ==================== FUNCIONES DE CONTRASEÑA ====================

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con el hash guardado."""
    return pwd_context.verify(plain_password, hashed_password)


def obtener_password_hash(password: str) -> str:
    """Genera un hash seguro para la contraseña del usuario."""
    return pwd_context.hash(password)


# ==================== FUNCIONES DE JWT Y TOKEN ====================

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera un token de acceso JWT codificado con fecha de expiración."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.Usuario:
    """Valida el token bearer de la solicitud y recupera el usuario correspondiente."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if usuario is None:
        raise credentials_exception
        
    return usuario


# ==================== CONTROL DE ROLES Y PERMISOS ====================

def requerir_rol(roles_permitidos: List[str]):
    """
    middleware / dependencia para restringir endpoints según el rol del usuario.
    Ejemplo de uso: Depends(security.requerir_rol(["admin", "entrenador"]))
    """
    def wrapper(current_user: models.Usuario = Depends(obtener_usuario_actual)):
        if current_user.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes los permisos necesarios para realizar esta acción."
            )
        return current_user
    return wrapper