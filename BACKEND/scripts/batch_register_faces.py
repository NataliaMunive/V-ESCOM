"""Script para registrar en lote imágenes de `fotos_rostros` en la base de datos.

Modo de uso (desde la carpeta BACKEND, con el entorno virtual activado):
  python scripts/batch_register_faces.py --dir fotos_rostros

El script admite dos estructuras de dataset:
  1) Subcarpetas por `id_persona` con imágenes dentro: fotos_rostros/123/img1.jpg
  2) Archivos en la raíz con prefijo `id_persona_`: fotos_rostros/123_img1.jpg

El script extrae embeddings usando `app.utils.face_utils.extraer_embedding`
y persiste registros en la tabla `rostros_autorizados`.
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


def iter_images(base_dir: Path) -> Iterable[Path]:
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                yield Path(root) / f


def obtener_id_desde_path(p: Path) -> int | None:
    # Preferir carpeta padre si es numérica
    try:
        parent = p.parent.name
        pid = int(parent)
        return pid
    except Exception:
        pass

    # Si no, intentar prefijo antes de '_' en el nombre del archivo
    name = p.name
    if '_' in name:
        pref = name.split('_', 1)[0]
        try:
            return int(pref)
        except Exception:
            return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='Directorio con imágenes (fotos_rostros)')
    ap.add_argument('--forzar', action='store_true', help='Forzar inserción aunque exista duplicado')
    args = ap.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print(f'No existe: {base}')
        return

    db = SessionLocal()
    try:
        for img_path in iter_images(base):
            pid = obtener_id_desde_path(img_path)
            if pid is None:
                print(f"Omitiendo (no se pudo inferir id_persona): {img_path}")
                continue

            persona = db.query(PersonaAutorizada).filter(PersonaAutorizada.id_persona == pid).first()
            if persona is None:
                print(f"Omitiendo (persona no encontrada id={pid}): {img_path}")
                continue

            try:
                contenido = img_path.read_bytes()
                emb = extraer_embedding(contenido)
            except Exception as e:
                print(f"Error extrayendo embedding {img_path}: {e}")
                continue

            # Verificar duplicados simples: buscar el vecino más cercano
            distancia = RostroAutorizado.embedding.cosine_distance(emb.tolist())
            duplicado = (
                db.query(RostroAutorizado, distancia.label('distancia'))
                .filter(RostroAutorizado.embedding.isnot(None))
                .order_by(distancia)
                .first()
            )

            if duplicado and not args.forzar:
                r, dist = duplicado
                simil = 1.0 - float(dist)
                print(f"Posible duplicado (sim={simil:.4f}) -> Omitiendo {img_path}. Use --forzar para forzar.")
                continue

            # Persistir
            ruta_rel = str(img_path)
            nuevo = RostroAutorizado(
                id_persona=pid,
                embedding=emb.tolist(),
                descripcion='Registro por lote',
                ruta_imagen=ruta_rel,
            )
            db.add(nuevo)
            db.commit()
            print(f"Registrado: id_persona={pid} -> {img_path}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
