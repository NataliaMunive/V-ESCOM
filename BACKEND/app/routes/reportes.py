from io import BytesIO
from datetime import date, time as time_type
from typing import Optional
 
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
 
from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.evento import EventoAcceso
 
router = APIRouter(prefix="/reportes", tags=["Reportes"])
 
 
def _generar_pdf(eventos: list, filtros: dict) -> bytes:
    """Genera el PDF del reporte usando ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.75 * inch,
    )
 
    # ── Colores institucionales ──────────────────────────────────────────────
    AZUL_IPN  = colors.HexColor("#0033A0")
    AZUL_CLARO = colors.HexColor("#1a52c9")
    ROJO      = colors.HexColor("#e63946")
    VERDE     = colors.HexColor("#2dc653")
    GRIS_BG   = colors.HexColor("#f2f4f8")
    GRIS_BORDE = colors.HexColor("#cbd5e1")
    TEXTO     = colors.HexColor("#1e293b")
 
    estilos = getSampleStyleSheet()
 
    estilo_titulo = ParagraphStyle(
        "titulo",
        parent=estilos["Normal"],
        fontSize=17,
        fontName="Helvetica-Bold",
        textColor=AZUL_IPN,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    estilo_subtitulo = ParagraphStyle(
        "subtitulo",
        parent=estilos["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=colors.HexColor("#64748b"),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    estilo_metadato = ParagraphStyle(
        "metadato",
        parent=estilos["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=colors.HexColor("#475569"),
        alignment=TA_LEFT,
    )
    estilo_encabezado_tabla = ParagraphStyle(
        "enc_tabla",
        parent=estilos["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )
 
    # ── Calcular estadísticas ────────────────────────────────────────────────
    total     = len(eventos)
    auth      = sum(1 for e in eventos if e.get("tipo_acceso") == "Autorizado")
    no_auth   = total - auth
    tasa_auth = f"{(auth / total * 100):.1f}%" if total > 0 else "—"
 
    # ── Contenido ────────────────────────────────────────────────────────────
    elementos = []
 
    # Encabezado
    elementos.append(Paragraph("V-ESCOM", estilo_titulo))
    elementos.append(Spacer(1, 2))
    elementos.append(Paragraph(
        "Sistema de Vigilancia con Reconocimiento Facial · ESCOM-IPN",
        estilo_subtitulo,
    ))
    elementos.append(HRFlowable(
        width="100%", thickness=2, color=AZUL_IPN, spaceAfter=8
    ))
 
    # Subtítulo del reporte
    elementos.append(Paragraph(
        "<b>Reporte de Eventos de Acceso</b>",
        ParagraphStyle("rt", parent=estilos["Normal"],
                       fontSize=13, fontName="Helvetica-Bold",
                       textColor=TEXTO, spaceAfter=4),
    ))
 
    # Filtros aplicados
    desde  = filtros.get("fecha_desde") or "—"
    hasta  = filtros.get("fecha_hasta") or "—"
    tipo   = filtros.get("tipo") or "Todos"
    camara = filtros.get("id_camara") or "Todas"
 
    elementos.append(Paragraph(
        f"Período: <b>{desde}</b> a <b>{hasta}</b>   |   "
        f"Tipo: <b>{tipo}</b>   |   Cámara: <b>{camara}</b>",
        estilo_metadato,
    ))
    elementos.append(Spacer(1, 10))
 
    # Tarjetas de resumen
    resumen_data = [
        ["Total", "Autorizados", "No Autorizados", "Tasa de Autorización"],
        [str(total), str(auth), str(no_auth), tasa_auth],
    ]
    resumen_table = Table(resumen_data, colWidths=[1.6 * inch] * 4)
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), AZUL_IPN),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (-1, 1), 15),
        ("TEXTCOLOR",    (0, 1), (0, 1), AZUL_IPN),
        ("TEXTCOLOR",    (1, 1), (1, 1), VERDE),
        ("TEXTCOLOR",    (2, 1), (2, 1), ROJO),
        ("TEXTCOLOR",    (3, 1), (3, 1), AZUL_CLARO),
        ("BACKGROUND",   (0, 1), (-1, 1), GRIS_BG),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [GRIS_BG]),
        ("GRID",         (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elementos.append(resumen_table)
    elementos.append(Spacer(1, 14))
 
    # Tabla de eventos
    encabezados = [
        Paragraph(h, estilo_encabezado_tabla)
        for h in ["# Evento", "Tipo de Acceso", "Fecha", "Hora", "Cámara", "Persona ID", "Similitud"]
    ]
    filas = [encabezados]
 
    for ev in eventos:
        sim = ev.get("similitud")
        sim_str = f"{sim * 100:.1f}%" if sim is not None else "—"
        tipo_ev = ev.get("tipo_acceso", "—")
 
        fila = [
            Paragraph(f"#{ev.get('id_evento', '—')}", ParagraphStyle("mono",
                parent=estilos["Normal"], fontSize=8,
                textColor=colors.HexColor("#64748b"), alignment=TA_CENTER)),
            Paragraph(tipo_ev, ParagraphStyle("tipo",
                parent=estilos["Normal"], fontSize=8,
                textColor=VERDE if tipo_ev == "Autorizado" else ROJO,
                fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(str(ev.get("fecha") or "—"), ParagraphStyle("cel",
                parent=estilos["Normal"], fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(ev.get("hora") or "—")[:8], ParagraphStyle("cel",
                parent=estilos["Normal"], fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(ev.get("id_camara") or "—"), ParagraphStyle("cel",
                parent=estilos["Normal"], fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(ev.get("id_persona") or "—"), ParagraphStyle("cel",
                parent=estilos["Normal"], fontSize=8, alignment=TA_CENTER)),
            Paragraph(sim_str, ParagraphStyle("cel",
                parent=estilos["Normal"], fontSize=8, alignment=TA_CENTER)),
        ]
        filas.append(fila)
 
    col_widths = [0.9*inch, 1.4*inch, 1.0*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.9*inch]
    tabla_eventos = Table(filas, colWidths=col_widths, repeatRows=1)
    tabla_eventos.setStyle(TableStyle([
        # encabezado
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_IPN),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # filas alternas
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, GRIS_BG]),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla_eventos)
 
    # Pie de página con fecha de generación
    elementos.append(Spacer(1, 16))
    elementos.append(HRFlowable(
        width="100%", thickness=0.5, color=GRIS_BORDE, spaceBefore=4
    ))
    from datetime import datetime
    elementos.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · V-ESCOM · ESCOM-IPN",
        ParagraphStyle("pie", parent=estilos["Normal"],
                       fontSize=7, textColor=colors.HexColor("#94a3b8"),
                       alignment=TA_CENTER, spaceBefore=4),
    ))
 
    doc.build(elementos)
    buffer.seek(0)
    return buffer.read()
 
 
@router.get("/pdf", summary="Exportar reporte de eventos en PDF")
def exportar_reporte_pdf(
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin   YYYY-MM-DD"),
    tipo: Optional[str] = Query(None, description="'Autorizado' o 'No Autorizado'"),
    id_camara: Optional[int] = Query(None),
    limit: int = Query(500, le=1000),
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Genera y descarga un reporte de eventos de acceso en formato PDF.
    Aplica los mismos filtros que la vista de Reportes del frontend.
    """
    query = db.query(EventoAcceso)
 
    if tipo:
        query = query.filter(EventoAcceso.tipo_acceso == tipo)
    if id_camara:
        query = query.filter(EventoAcceso.id_camara == id_camara)
 
    eventos_orm = query.order_by(EventoAcceso.fecha.desc(), EventoAcceso.hora.desc()).limit(limit).all()
 
    # Filtrar por fechas (en Python, igual que el frontend)
    def _str(v):
        if v is None:
            return None
        if isinstance(v, (date,)):
            return v.isoformat()
        return str(v)
 
    eventos = []
    for ev in eventos_orm:
        fecha_str = _str(ev.fecha)
        if fecha_desde and fecha_str and fecha_str < fecha_desde:
            continue
        if fecha_hasta and fecha_str and fecha_str > fecha_hasta:
            continue
        hora_str = str(ev.hora) if isinstance(ev.hora, time_type) else str(ev.hora or "")
        eventos.append({
            "id_evento":   ev.id_evento,
            "tipo_acceso": ev.tipo_acceso,
            "fecha":       fecha_str,
            "hora":        hora_str,
            "id_camara":   ev.id_camara,
            "id_persona":  ev.id_persona,
            "similitud":   ev.similitud,
        })
 
    filtros = {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "tipo":        tipo or "Todos",
        "id_camara":   id_camara or "Todas",
    }
 
    pdf_bytes = _generar_pdf(eventos, filtros)
 
    from datetime import datetime
    nombre_archivo = (
        f"reporte_vescom_{fecha_desde or 'inicio'}_{fecha_hasta or 'hoy'}.pdf"
    )
 
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )