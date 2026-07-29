from database import SessionLocal
import models
from main import calcular_edad_y_categoria

def actualizar_atletas_a_categorias_pares():
    db = SessionLocal()
    try:
        atletas = db.query(models.Atleta).all()
        modificados = 0

        for atleta in atletas:
            if atleta.fecha_nacimiento:
                edad, nueva_categoria = calcular_edad_y_categoria(atleta.fecha_nacimiento)
                if atleta.categoria != nueva_categoria or atleta.edad != edad:
                    atleta.edad = edad
                    atleta.categoria = nueva_categoria
                    modificados += 1

        db.commit()
        print(f"⚽ ¡Listo! Se actualizaron {modificados} atletas a sus categorías pares correspondientes.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al actualizar: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    actualizar_atletas_a_categorias_pares()