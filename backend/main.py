from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

import security
import models, schemas
from database import engine, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arabito FC Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"mensaje": "API de Arabito FC funcionando correctamente"}

# --- FUNCIÓN LÓGICA: CALCULAR EDAD Y CATEGORÍA ---
def calcular_edad_y_categoria(fecha_nacimiento: date):
    if not fecha_nacimiento:
        return None, None
        
    hoy = date.today()
    # Calcula la edad exacta restando años y ajustando si aún no ha cumplido este año
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    
    categoria = "Sin categoría"
    if edad < 4:
        categoria = "Iniciación (Menor de 4)"
    elif 4 <= edad <= 5:
        categoria = "Sub-6"
    elif 6 <= edad <= 7:
        categoria = "Sub-8"
    elif 8 <= edad <= 9:
        categoria = "Sub-10"
    elif 10 <= edad <= 11:
        categoria = "Sub-12"
    elif 12 <= edad <= 13:
        categoria = "Sub-14"
    elif 14 <= edad <= 15:
        categoria = "Sub-16"
    elif 16 <= edad <= 17:
        categoria = "Sub-18"
    elif 18 <= edad <= 19:
        categoria = "Sub-20"
    else:
        categoria = "Mayor/Libre"
        
    return edad, categoria

# --- RUTAS DE AUTENTICACIÓN Y USUARIOS ---
@app.post("/usuarios/registro", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    hashed_password = security.obtener_password_hash(usuario.password)
    nuevo_usuario = models.Usuario(email=usuario.email, hashed_password=hashed_password, rol=usuario.rol)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not usuario or not security.verificar_password(form_data.password, usuario.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    
    access_token_expires = security.timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.crear_access_token(data={"sub": usuario.email, "rol": usuario.rol}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# --- RUTAS DE ATLETAS (CRUD) ---
@app.post("/atletas/", response_model=schemas.Atleta, status_code=status.HTTP_201_CREATED)
def crear_atleta(atleta: schemas.AtletaCreate, db: Session = Depends(get_db)):
    db_atleta = db.query(models.Atleta).filter(models.Atleta.cedula == atleta.cedula).first()
    if db_atleta:
        raise HTTPException(status_code=400, detail="La cédula ya está registrada.")
    
    datos_atleta = atleta.model_dump(exclude_unset=True) if hasattr(atleta, 'model_dump') else atleta.dict(exclude_unset=True)
    
    # Asignación automática de edad y categoría
    if atleta.fecha_nacimiento:
        edad, categoria = calcular_edad_y_categoria(atleta.fecha_nacimiento)
        datos_atleta["edad"] = edad
        datos_atleta["categoria"] = categoria

    nuevo_atleta = models.Atleta(**datos_atleta)
    db.add(nuevo_atleta)
    db.commit()
    db.refresh(nuevo_atleta)
    return nuevo_atleta

@app.get("/atletas/", response_model=List[schemas.Atleta])
def listar_atletas(cedula: Optional[str] = Query(None), categoria: Optional[str] = Query(None), nombre: Optional[str] = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Atleta)
    if cedula:
        query = query.filter(models.Atleta.cedula == cedula)
    if categoria:
        query = query.filter(models.Atleta.categoria == categoria)
    if nombre:
        busqueda = f"%{nombre}%"
        query = query.filter((models.Atleta.nombre.ilike(busqueda)) | (models.Atleta.apellido.ilike(busqueda)))
    return query.offset(skip).limit(limit).all()

@app.get("/atletas/{atleta_id}", response_model=schemas.Atleta)
def obtener_atleta(atleta_id: int, db: Session = Depends(get_db)):
    atleta = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    return atleta

@app.put("/atletas/{atleta_id}", response_model=schemas.Atleta)
def actualizar_atleta(atleta_id: int, atleta_actualizado: schemas.AtletaCreate, db: Session = Depends(get_db)):
    atleta_db = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta_db:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    
    datos_actualizados = atleta_actualizado.model_dump(exclude_unset=True) if hasattr(atleta_actualizado, 'model_dump') else atleta_actualizado.dict(exclude_unset=True)
    
    # Recalcular si se cambia la fecha de nacimiento
    if "fecha_nacimiento" in datos_actualizados and datos_actualizados["fecha_nacimiento"]:
        edad, categoria = calcular_edad_y_categoria(datos_actualizados["fecha_nacimiento"])
        datos_actualizados["edad"] = edad
        datos_actualizados["categoria"] = categoria

    for key, value in datos_actualizados.items():
        setattr(atleta_db, key, value)
    
    db.commit()
    db.refresh(atleta_db)
    return atleta_db

@app.delete("/atletas/{atleta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_atleta(atleta_id: int, db: Session = Depends(get_db)):
    atleta_db = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta_db:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    db.delete(atleta_db)
    db.commit()
    return None

# --- RUTAS DE FICHAS MÉDICAS (CRUD COMPLETO) ---
@app.post("/fichas-medicas/", response_model=schemas.FichaMedica, status_code=status.HTTP_201_CREATED)
def crear_ficha_medica(ficha: schemas.FichaMedicaCreate, db: Session = Depends(get_db)):
    atleta = db.query(models.Atleta).filter(models.Atleta.id == ficha.atleta_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="El atleta no existe.")
    
    ficha_existente = db.query(models.FichaMedica).filter(models.FichaMedica.atleta_id == ficha.atleta_id).first()
    if ficha_existente:
        raise HTTPException(status_code=400, detail="Este atleta ya cuenta con una ficha médica registrada.")

    datos_ficha = ficha.model_dump(exclude_unset=True) if hasattr(ficha, 'model_dump') else ficha.dict(exclude_unset=True)
    nueva_ficha = models.FichaMedica(**datos_ficha)
    db.add(nueva_ficha)
    db.commit()
    db.refresh(nueva_ficha)
    return nueva_ficha

@app.get("/fichas-medicas/{atleta_id}", response_model=schemas.FichaMedica)
def obtener_ficha_medica(atleta_id: int, db: Session = Depends(get_db)):
    ficha = db.query(models.FichaMedica).filter(models.FichaMedica.atleta_id == atleta_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada.")
    return ficha

@app.put("/fichas-medicas/{ficha_id}", response_model=schemas.FichaMedica)
def actualizar_ficha_medica(ficha_id: int, ficha_actualizada: schemas.FichaMedicaCreate, db: Session = Depends(get_db)):
    ficha_db = db.query(models.FichaMedica).filter(models.FichaMedica.id == ficha_id).first()
    if not ficha_db:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada")
    
    datos_actualizados = ficha_actualizada.model_dump(exclude_unset=True) if hasattr(ficha_actualizada, 'model_dump') else ficha_actualizada.dict(exclude_unset=True)
    
    for key, value in datos_actualizados.items():
        setattr(ficha_db, key, value)
    
    db.commit()
    db.refresh(ficha_db)
    return ficha_db

@app.delete("/fichas-medicas/{ficha_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ficha_medica(ficha_id: int, db: Session = Depends(get_db)):
    ficha_db = db.query(models.FichaMedica).filter(models.FichaMedica.id == ficha_id).first()
    if not ficha_db:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada")
    
    db.delete(ficha_db)
    db.commit()
    return None