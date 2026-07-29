from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generar_pdf_reporte_solvencia(atletas_deuda, resumen_datos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloReporte',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=10
    )
    
    subtitulo_style = ParagraphStyle(
        'SubTituloReporte',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#4A5568"),
        alignment=1,
        spaceAfter=20
    )
    
    # Encabezado
    elements.append(Paragraph("<b>ARABITO FC - ACADEMIA DE FÚTBOL</b>", titulo_style))
    elements.append(Paragraph(f"<b>REPORTE FINANCIERO Y ESTADO DE CUENTA DE ATLETAS</b><br/>Fecha de Emisión: {date.today().strftime('%d/%m/%Y')}", subtitulo_style))
    elements.append(Spacer(1, 10))
    
    # Cuadro de Resumen General
    datos_resumen = [
        ["Total Atletas", "Solventes", "Deudores", "Deuda Total Estimada"],
        [
            str(resumen_datos["total_atletas"]),
            str(resumen_datos["total_solventes"]),
            str(resumen_datos["total_deudores"]),
            f"${resumen_datos['monto_total_pendiente']:.2f}"
        ]
    ]
    
    tabla_resumen = Table(datos_resumen, colWidths=[130, 130, 130, 130])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#EDF2F7")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
    ]))
    
    elements.append(tabla_resumen)
    elements.append(Spacer(1, 20))
    
    # Tabla Detallada de Atletas y Meses que deben
    elements.append(Paragraph("<b>DESGLOSE DE PAGOS Y MESES PENDIENTES</b>", styles['Heading2']))
    elements.append(Spacer(1, 8))
    
    encabezados_tabla = ["Atleta", "Categoría", "Contacto", "Estatus", "Meses Debe", "Deuda ($)"]
    data_atletas = [encabezados_tabla]
    
    for item in atletas_deuda:
        nombre = item["nombre_completo"]
        categoria = item["categoria"]
        contacto = item["contacto"]
        estatus = item["estatus_solvencia"]
        meses = str(item["meses_adeudados"]) if item["meses_adeudados"] > 0 else "-"
        deuda = f"${item['monto_total_deuda']:.2f}" if item["monto_total_deuda"] > 0 else "$0.00"
        
        data_atletas.append([nombre, categoria, contacto, estatus, meses, deuda])
        
    tabla_atletas = Table(data_atletas, colWidths=[140, 70, 130, 70, 50, 60])
    
    estilo_tabla_atletas = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A202C")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]
    
    for i, item in enumerate(atletas_deuda, start=1):
        if item["estatus_solvencia"] == "Solvente":
            estilo_tabla_atletas.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor("#2F855A")))
        else:
            estilo_tabla_atletas.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor("#C53030")))
            estilo_tabla_atletas.append(('TEXTCOLOR', (5, i), (5, i), colors.HexColor("#C53030")))
            estilo_tabla_atletas.append(('FONTNAME', (3, i), (-1, i), 'Helvetica-Bold'))
            
    tabla_atletas.setStyle(TableStyle(estilo_tabla_atletas))
    elements.append(tabla_atletas)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer