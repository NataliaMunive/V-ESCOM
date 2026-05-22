"""Script para registrar en lote imágenes de `fotos_rostros` en la base de datos.

Modo de uso (desde la carpeta BACKEND, con el entorno virtual activado):
  python entrenamiento/registrar_rostros_lote.py --dir fotos_rostros

El script admite dos estructuras de dataset:
  1) Subcarpetas por `id_persona` con imágenes dentro: fotos_rostros/123/img1.jpg
  2) Archivos en la raíz con prefijo `id_persona_`:   fotos_rostros/123_img1.jpg

El script extrae embeddings usando `app.utils.face_utils.extraer_embedding`
y persiste registros en la tabla `rostros_autorizados`.

Mejoras aplicadas:
  - Detección de duplicados filtrada por persona (no en toda la BD)
  - Commit por lotes cada TAMANIO_LOTE imágenes (más eficiente)
  - Contadores de resumen al finalizar
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from app.bd import SessionLocal
from app.models.persona_autorizada import PersonaAutorizada
from app.models.rostro_autorizado import RostroAutorizado
from app.utils.face_utils import extraer_embedding

# Número de imágenes entre cada commit a la BD
TAMANIO_LOTE = 10


def iterar_imagenes(directorio_base: Path) -> Iterable[Path]:
    """Recorre recursivamente el directorio y devuelve rutas de imágenes válidas."""
    for raiz, _, archivos in os.walk(directorio_base):
        for nombre_archivo in archivos:
            if nombre_archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
                yield Path(raiz) / nombre_archivo


def obtener_id_desde_ruta(ruta: Path) -> int | None:
    """Infiere el id_persona a partir de la ruta de la imagen.

    Estrategia 1: carpeta padre numérica  → fotos_rostros/42/foto.jpg
    Estrategia 2: prefijo numérico en el nombre → fotos_rostros/42_foto.jpg
    """
    # Estrategia 1: carpeta padre numérica
    try:
        nombre_carpeta = ruta.parent.name
        id_persona = int(nombre_carpeta)
        return id_persona
    except (ValueError, TypeError):
        pass

    # Estrategia 2: prefijo antes del primer '_'
    nombre = ruta.name
    if '_' in nombre:
        prefijo = nombre.split('_', 1)[0]
        try:
            return int(prefijo)
        except (ValueError, TypeError):
            return None

    return None


def main():
    analizador = argparse.ArgumentParser(
        description="Registra en lote imágenes de rostros en la base de datos."
    )
    analizador.add_argument(
        '--dir', required=True,
        help='Directorio raíz con imágenes (ej. fotos_rostros)'
    )
    analizador.add_argument(
        '--forzar', action='store_true',
        help='Forzar inserción aunque exista un posible duplicado'
    )
    analizador.add_argument(
        '--umbral-similitud', type=float, default=0.90,
        help='Similitud coseno mínima para considerar duplicado (por defecto 0.90)'
    )
    argumentos = analizador.parse_args()

    directorio_base = Path(argumentos.dir)
    if not directorio_base.exists():
        print(f'[ERROR] El directorio no existe: {directorio_base}')
        return

    sesion_bd = SessionLocal()

    # Contadores para el resumen final
    total_procesadas = 0
    total_registradas = 0
    total_omitidas_duplicado = 0
    total_errores = 0
    contador_lote = 0

    try:
        for ruta_imagen in iterar_imagenes(directorio_base):
            total_procesadas += 1

            # ── 1. Inferir id_persona ─────────────────────────────────────────
            id_persona = obtener_id_desde_ruta(ruta_imagen)
            if id_persona is None:
                print(f"  [OMITIDA] No se pudo inferir id_persona: {ruta_imagen}")
                total_errores += 1
                continue

            # ── 2. Verificar que la persona exista en la BD ───────────────────
            persona = (
                sesion_bd.query(PersonaAutorizada)
                .filter(PersonaAutorizada.id_persona == id_persona)
                .first()
            )
            if persona is None:
                print(f"  [OMITIDA] Persona no encontrada (id={id_persona}): {ruta_imagen}")
                total_errores += 1
                continue

            # ── 3. Extraer embedding ──────────────────────────────────────────
            try:
                contenido_bytes = ruta_imagen.read_bytes()
                embedding = extraer_embedding(contenido_bytes)
            except Exception as error:
                print(f"  [ERROR] Extrayendo embedding de {ruta_imagen}: {error}")
                total_errores += 1
                continue

            # ── 4. Verificar duplicados SOLO dentro de la misma persona ───────
            distancia_coseno = RostroAutorizado.embedding.cosine_distance(embedding.tolist())
            posible_duplicado = (
                sesion_bd.query(RostroAutorizado, distancia_coseno.label('distancia'))
                .filter(RostroAutorizado.id_persona == id_persona)          # ← solo su persona
                .filter(RostroAutorizado.embedding.isnot(None))
                .order_by(distancia_coseno)
                .first()
            )

            if posible_duplicado and not argumentos.forzar:
                rostro, dist = posible_duplicado
                similitud = 1.0 - float(dist)
                if similitud >= argumentos.umbral_similitud:
                    print(
                        f"  [DUPLICADO] sim={similitud:.4f} ≥ {argumentos.umbral_similitud} "
                        f"→ Omitiendo {ruta_imagen.name}. Usa --forzar para ignorar."
                    )
                    total_omitidas_duplicado += 1
                    continue

            # ── 5. Persistir en la BD ─────────────────────────────────────────
            ruta_relativa = str(ruta_imagen)
            nuevo_rostro = RostroAutorizado(
                id_persona=id_persona,
                embedding=embedding.tolist(),
                descripcion='Registro por lote',
                ruta_imagen=ruta_relativa,
            )
            sesion_bd.add(nuevo_rostro)
            contador_lote += 1
            total_registradas += 1
            print(f"  [OK] id_persona={id_persona} → {ruta_imagen.name}")

            # Commit cada TAMANIO_LOTE inserciones para mayor eficiencia
            if contador_lote % TAMANIO_LOTE == 0:
                sesion_bd.commit()
                print(f"  [BD] Commit parcial ({contador_lote} registros acumulados)")

        # Commit final con los registros restantes
        sesion_bd.commit()

    except Exception as error_general:
        sesion_bd.rollback()
        print(f"\n[ERROR CRÍTICO] Se realizó rollback: {error_general}")
        raise

    finally:
        sesion_bd.close()

    # ── Resumen ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("RESUMEN DEL REGISTRO EN LOTE")
    print("=" * 50)
    print(f"  Imágenes procesadas : {total_procesadas}")
    print(f"  Registradas en BD   : {total_registradas}")
    print(f"  Omitidas (duplicado): {total_omitidas_duplicado}")
    print(f"  Errores / omitidas  : {total_errores}")
    print("=" * 50)


if __name__ == '__main__':
    main()
