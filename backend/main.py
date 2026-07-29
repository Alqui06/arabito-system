from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta

# Importaciones locales
import models
import schemas
import security
from database import engine, get_db, SessionLocal
from pdf_generator import generar_pdf_reporte_solvencia

# Precios de referencia para la academia Arabito FC
PRECIO_INSCRIPCION = 20.0
PRECIO_MENSUALIDAD = 15.0

# Crear las tablas en la base de datos automáticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Arabito FC Web API",
    description="Sistema Backend completo para el control de atletas, fichas médicas, pagos y solvencias de Arabito FC",
    version="1.2.0"
)

# Configuración de CORS para conectar con el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- INICIALIZACIÓN AUTOMÁTICA DEL SUPERADMIN ---
def crear_superadmin_inicial():
    """Verifica si existe un administrador. Si no existe, crea la cuenta maestra."""
    db: Session = SessionLocal()
    try:
        admin_existente = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        if not admin_existente:
            email_superadmin = "admin@arabitofc.com"
            password_superadmin = "Arabito2026*"
            
            hashed_pw = security.obtener_password_hash(password_superadmin)
            nuevo_superadmin = models.Usuario(
                email=email_superadmin,
                hashed_password=hashed_pw,
                rol="admin"
            )
            db.add(nuevo_superadmin)
            db.commit()
            print(f"✅ [INICIO] Superadmin inicial creado: {email_superadmin} | Clave: {password_superadmin}")
        else:
            print("ℹ️ [INICIO] El usuario Superadmin ya existe en la base de datos.")
    except Exception as e:
        print(f"❌ [ERROR] Falló la creación del Superadmin inicial: {e}")
        db.rollback()
    finally:
        db.close()

# Evento de arranque de FastAPI
@app.on_event("startup")
def al_arrancar():
    crear_superadmin_inicial()


@app.get("/", tags=["Estado"])
def read_root():
    return {"mensaje": "API de Arabito FC funcionando correctamente"}


# --- LÓGICA DE NEGOCIO: CÁLCULO DE EDAD Y CATEGORÍA (RANGOS PARES) ---
# --- LÓGICA DE NEGOCIO: CÁLCULO DE EDAD Y CATEGORÍA (ESTRICTAMENTE PAR) ---
def calcular_edad_y_categoria(fecha_nacimiento: date):
    if not fecha_nacimiento:
        return None, None
        
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    
    if edad <= 6:
        categoria = "Sub-6"
    elif 7 <= edad <= 8:
        categoria = "Sub-8"
    elif 9 <= edad <= 10:
        categoria = "Sub-10"
    elif 11 <= edad <= 12:
        categoria = "Sub-12"
    elif 13 <= edad <= 14:
        categoria = "Sub-14"
    elif 15 <= edad <= 16:
        categoria = "Sub-16"
    elif 17 <= edad <= 18:
        categoria = "Sub-18"
    elif 19 <= edad <= 20:
        categoria = "Sub-20"
    else:
        categoria = "Libre"
        
    return edad, categoria


# --- AUTENTICACIÓN Y SEGURIDAD ---

@app.post("/usuarios/registro", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED, tags=["Autenticación"])
def registrar_usuario(
    usuario: schemas.UsuarioCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"])) # Solo Admin puede crear nuevos usuarios
):
    db_usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    hashed_password = security.obtener_password_hash(usuario.password)
    nuevo_usuario = models.Usuario(email=usuario.email, hashed_password=hashed_password, rol=usuario.rol)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/token", response_model=schemas.Token, tags=["Autenticación"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not usuario or not security.verificar_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.crear_access_token(
        data={"sub": usuario.email, "rol": usuario.rol}, 
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": usuario.rol,
        "email": usuario.email
    }

@app.get("/usuarios/", response_model=List[schemas.Usuario], tags=["Autenticación"])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    return db.query(models.Usuario).all()

@app.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Autenticación"])
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    if current_user.id == usuario_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta activa.")
    
    usuario_db = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    db.delete(usuario_db)
    db.commit()
    return None


# --- GESTIÓN DE ATLETAS ---

@app.post("/atletas/", response_model=schemas.Atleta, status_code=status.HTTP_201_CREATED, tags=["Atletas"])
def crear_atleta(
    atleta: schemas.AtletaCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    # 1. Cédula opcional: sólo verifica si fue provista
    if atleta.cedula:
        db_atleta = db.query(models.Atleta).filter(models.Atleta.cedula == atleta.cedula).first()
        if db_atleta:
            raise HTTPException(status_code=400, detail="La cédula ya está registrada.")
    
    # 2. Convertir esquema a diccionario
    datos_atleta = atleta.model_dump(exclude_unset=True) if hasattr(atleta, 'model_dump') else atleta.dict(exclude_unset=True)
    
    # 3. Extraer los datos del representante antes de borrarlo del diccionario de Atleta
    datos_representante = datos_atleta.pop("representante", None)

    if atleta.fecha_nacimiento:
        edad, categoria = calcular_edad_y_categoria(atleta.fecha_nacimiento)
        datos_atleta["edad"] = edad
        datos_atleta["categoria"] = categoria

    # 4. Si vienen datos del representante, crearlo o asociarlo primero
    if datos_representante:
        # Si tienes una tabla/modelo llamado Representante:
        # nuevo_rep = models.Representante(**datos_representante)
        # db.add(nuevo_rep)
        # db.flush() # Genera el ID del representante
        # datos_atleta["representante_id"] = nuevo_rep.id
        pass

    # 5. Crear el atleta
    nuevo_atleta = models.Atleta(**datos_atleta)
    db.add(nuevo_atleta)
    db.commit()
    db.refresh(nuevo_atleta)
    return nuevo_atleta

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

# Asumiendo tus importaciones previas...

@app.get("/atletas/", response_model=List[schemas.Atleta], tags=["Atletas"])
def listar_atletas(
    cedula: Optional[str] = Query(None, description="Filtrar por cédula exacta"), 
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"), 
    nombre: Optional[str] = Query(None, description="Buscar por nombre o apellido"), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=500), 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    query = db.query(models.Atleta)

    if cedula:
        # Si la cédula es única o exacta, conviene limpiar espacios
        query = query.filter(models.Atleta.cedula == cedula.strip())
        
    if categoria:
        query = query.filter(models.Atleta.categoria == categoria)
        
    if nombre:
        busqueda = f"%{nombre.strip()}%"
        # Permite buscar "Carlos", "Pérez" o "Carlos Pérez"
        query = query.filter(
            func.concat(models.Atleta.nombre, ' ', models.Atleta.apellido).ilike(busqueda)
        )

    # Ordenar por defecto suele ser útil para paginaciones consistentes
    return query.order_by(models.Atleta.id.asc()).offset(skip).limit(limit).all()

@app.get("/atletas/morosos/", response_model=List[schemas.Atleta], tags=["Atletas"])
def listar_atletas_deudores(
    categoria: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    query = db.query(models.Atleta).filter(models.Atleta.estatus_solvencia == "Deudor")
    if categoria:
        query = query.filter(models.Atleta.categoria == categoria)
    return query.all()

@app.get("/atletas/{atleta_id}", response_model=schemas.Atleta, tags=["Atletas"])
def obtener_atleta(
    atleta_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    atleta = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    return atleta

@app.put("/atletas/{atleta_id}", response_model=schemas.Atleta, tags=["Atletas"])
def actualizar_atleta(
    atleta_id: int, 
    atleta_actualizado: schemas.AtletaCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    atleta_db = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta_db:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    
    datos_actualizados = atleta_actualizado.model_dump(exclude_unset=True) if hasattr(atleta_actualizado, 'model_dump') else atleta_actualizado.dict(exclude_unset=True)
    
    if "fecha_nacimiento" in datos_actualizados and datos_actualizados["fecha_nacimiento"]:
        edad, categoria = calcular_edad_y_categoria(datos_actualizados["fecha_nacimiento"])
        datos_actualizados["edad"] = edad
        datos_actualizados["categoria"] = categoria

    for key, value in datos_actualizados.items():
        setattr(atleta_db, key, value)
    
    db.commit()
    db.refresh(atleta_db)
    return atleta_db

@app.delete("/atletas/{atleta_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Atletas"])
def eliminar_atleta(
    atleta_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    atleta_db = db.query(models.Atleta).filter(models.Atleta.id == atleta_id).first()
    if not atleta_db:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    db.delete(atleta_db)
    db.commit()
    return None

@app.post("/atletas/reiniciar-solvencias", status_code=status.HTTP_200_OK, tags=["Atletas"])
def reiniciar_solvencia_mensual(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    db.query(models.Atleta).update({models.Atleta.estatus_solvencia: "Deudor"})
    db.commit()
    return {"mensaje": "Se ha actualizado el estatus de todos los atletas a 'Deudor' exitosamente."}


# --- FICHAS MÉDICAS ---

@app.post("/fichas-medicas/", response_model=schemas.FichaMedica, status_code=status.HTTP_201_CREATED, tags=["Fichas Médicas"])
def crear_ficha_medica(
    ficha: schemas.FichaMedicaCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
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

@app.get("/fichas-medicas/{atleta_id}", response_model=schemas.FichaMedica, tags=["Fichas Médicas"])
def obtener_ficha_medica(
    atleta_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    ficha = db.query(models.FichaMedica).filter(models.FichaMedica.atleta_id == atleta_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada.")
    return ficha

@app.put("/fichas-medicas/{ficha_id}", response_model=schemas.FichaMedica, tags=["Fichas Médicas"])
def actualizar_ficha_medica(
    ficha_id: int, 
    ficha_actualizada: schemas.FichaMedicaCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    ficha_db = db.query(models.FichaMedica).filter(models.FichaMedica.id == ficha_id).first()
    if not ficha_db:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada")
    
    datos_actualizados = ficha_actualizada.model_dump(exclude_unset=True) if hasattr(ficha_actualizada, 'model_dump') else ficha_actualizada.dict(exclude_unset=True)
    
    for key, value in datos_actualizados.items():
        setattr(ficha_db, key, value)
    
    db.commit()
    db.refresh(ficha_db)
    return ficha_db

@app.delete("/fichas-medicas/{ficha_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Fichas Médicas"])
def eliminar_ficha_medica(
    ficha_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    ficha_db = db.query(models.FichaMedica).filter(models.FichaMedica.id == ficha_id).first()
    if not ficha_db:
        raise HTTPException(status_code=404, detail="Ficha médica no encontrada")
    
    db.delete(ficha_db)
    db.commit()
    return None


# --- PAGOS, FINANZAS Y REPORTES EN PDF ---

@app.post("/pagos/", response_model=schemas.Pago, status_code=status.HTTP_201_CREATED, tags=["Pagos y Finanzas"])
def registrar_pago(
    pago: schemas.PagoCreate, 
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    atleta = db.query(models.Atleta).filter(models.Atleta.id == pago.atleta_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="El atleta referenciado no existe.")

    datos_pago = pago.model_dump() if hasattr(pago, 'model_dump') else pago.dict()
    nuevo_pago = models.Pago(**datos_pago)
    
    # Al registrar el pago, se marca al atleta como Solvente automáticamente
    atleta.estatus_solvencia = "Solvente"
    
    db.add(nuevo_pago)
    db.commit()
    db.refresh(nuevo_pago)
    return nuevo_pago

@app.get("/pagos/", response_model=List[schemas.Pago], tags=["Pagos y Finanzas"])
def listar_todos_los_pagos(
    metodo_pago: Optional[str] = Query(None),
    concepto: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    query = db.query(models.Pago)
    if metodo_pago:
        query = query.filter(models.Pago.metodo_pago.ilike(f"%{metodo_pago}%"))
    if concepto:
        query = query.filter(models.Pago.concepto.ilike(f"%{concepto}%"))
    return query.order_by(models.Pago.fecha_pago.desc()).offset(skip).limit(limit).all()

@app.get("/pagos/atleta/{atleta_id}", response_model=List[schemas.Pago], tags=["Pagos y Finanzas"])
def listar_pagos_atleta(
    atleta_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    return db.query(models.Pago).filter(models.Pago.atleta_id == atleta_id).all()

@app.get("/reportes/solvencia", response_model=schemas.ResumenSolvencia, tags=["Reportes"])
def obtener_reporte_solvencia(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    total_atletas = db.query(models.Atleta).count()
    if total_atletas == 0:
        return {"total_atletas": 0, "total_solventes": 0, "total_deudores": 0, "porcentaje_solvencia": 0.0}

    total_solventes = db.query(models.Atleta).filter(models.Atleta.estatus_solvencia == "Solvente").count()
    total_deudores = db.query(models.Atleta).filter(models.Atleta.estatus_solvencia == "Deudor").count()
    porcentaje = round((total_solventes / total_atletas) * 100, 2)

    return {
        "total_atletas": total_atletas,
        "total_solventes": total_solventes,
        "total_deudores": total_deudores,
        "porcentaje_solvencia": porcentaje
    }

@app.get("/reportes/finanzas", response_model=schemas.ResumenFinanciero, tags=["Reportes"])
def obtener_resumen_financiero(
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    query = db.query(models.Pago)
    if fecha_inicio:
        query = query.filter(models.Pago.fecha_pago >= fecha_inicio)
    if fecha_fin:
        query = query.filter(models.Pago.fecha_pago <= fecha_fin)

    pagos = query.all()
    total_recaudado = sum(pago.monto for pago in pagos)
    
    return {"total_recaudado": total_recaudado, "total_transacciones": len(pagos)}

@app.get("/reportes/solvencia/pdf", response_class=StreamingResponse, tags=["Reportes"])
def descargar_reporte_solvencia_pdf(
    categoria: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin"]))
):
    query = db.query(models.Atleta)
    if categoria:
        query = query.filter(models.Atleta.categoria == categoria)
        
    atletas = query.all()
    
    lista_desglose = []
    total_deuda_acumulada = 0.0
    total_solventes = 0
    total_deudores = 0

    for atleta in atletas:
        if atleta.estatus_solvencia == "Deudor":
            total_deudores += 1
            meses_debe = 1 
            deuda = meses_debe * PRECIO_MENSUALIDAD
        else:
            total_solventes += 1
            meses_debe = 0
            deuda = 0.0

        total_deuda_acumulada += deuda
        contacto_rep = f"{getattr(atleta, 'nombre_representante', None) or atleta.representante or 'S/I'} ({getattr(atleta, 'telefono_representante', None) or 'S/N'})"
        
        lista_desglose.append({
            "nombre_completo": f"{atleta.nombre} {atleta.apellido}",
            "categoria": atleta.categoria or "N/A",
            "contacto": contacto_rep,
            "estatus_solvencia": atleta.estatus_solvencia,
            "meses_adeudados": meses_debe,
            "monto_total_deuda": deuda
        })

    resumen = {
        "total_atletas": len(atletas),
        "total_solventes": total_solventes,
        "total_deudores": total_deudores,
        "monto_total_pendiente": total_deuda_acumulada
    }
    
    pdf_buffer = generar_pdf_reporte_solvencia(lista_desglose, resumen)
    headers = {'Content-Disposition': f'attachment; filename="Reporte_Morosidad_ArabitoFC_{date.today()}.pdf"'}
    
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@app.post("/fichas-medicas/", response_model=schemas.FichaMedica, status_code=status.HTTP_201_CREATED, tags=["Fichas Médicas"])
def guardar_o_actualizar_ficha(
    ficha: schemas.FichaMedicaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    # 1. Verificar si el atleta existe
    atleta = db.query(models.Atleta).filter(models.Atleta.id == ficha.atleta_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="El atleta especificado no existe.")

    # 2. Buscar si ya existe una ficha para este atleta
    ficha_db = db.query(models.FichaMedica).filter(models.FichaMedica.atleta_id == ficha.atleta_id).first()

    datos = ficha.model_dump() if hasattr(ficha, 'model_dump') else ficha.dict()

    if ficha_db:
        # Si ya existe, actualizamos los datos existentes
        for campo, valor in datos.items():
            setattr(ficha_db, campo, valor)
        db.commit()
        db.refresh(ficha_db)
        return ficha_db
    else:
        # Si no existe, creamos el nuevo registro
        nueva_ficha = models.FichaMedica(**datos)
        db.add(nueva_ficha)
        db.commit()
        db.refresh(nueva_ficha)
        return nueva_ficha

from sqlalchemy.orm import joinedload

@app.get("/fichas-medicas/", response_model=List[schemas.FichaMedica], tags=["Fichas Médicas"])
def listar_fichas_medicas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(security.requerir_rol(["admin", "entrenador"]))
):
    # Carga la relación 'atleta' implícitamente
    return db.query(models.FichaMedica)\
             .options(joinedload(models.FichaMedica.atleta))\
             .offset(skip)\
             .limit(limit)\
             .all()