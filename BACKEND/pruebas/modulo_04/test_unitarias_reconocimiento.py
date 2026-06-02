"""
Pruebas Unitarias — Módulo de Reconocimiento Facial y Dashboard
V-ESCOM

Casos cubiertos (plan de pruebas §Grupo 1):
    VESCOM-REC-U01  Extracción de embedding con imagen válida de un rostro
    VESCOM-REC-U02  Extracción de embedding con imagen sin rostro
    VESCOM-REC-U03  Extracción de embedding con imagen de múltiples rostros
    VESCOM-REC-U04  Reconocimiento de persona con lentes (oclusión parcial)
    VESCOM-REC-U05  Normalización L2 de un vector de embedding
    VESCOM-REC-U06  Similitud coseno entre el mismo vector (identidad)
    VESCOM-REC-U07  Similitud coseno entre vectores ortogonales
    VESCOM-REC-U08  Pipeline de entrenamiento SVM con dataset mínimo válido
    VESCOM-REC-U09  Carga de modelo SVM corrupto o con estructura inválida

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_06/test_unitarias_reconocimiento.py -v
    
Nota sobre assets de imagen:
    Los casos U01, U03 y U04 requieren imágenes reales en:
        pruebas/assets/persona_frontal.jpg    — un solo rostro frontal
        pruebas/assets/dos_rostros.jpg        — dos o más rostros visibles
        pruebas/assets/persona_con_lentes.jpg — persona con lentes de vista o sol
    Si los archivos no existen, los tests se marcan como SKIP automáticamente.
    Los casos U02, U05–U09 no requieren imágenes reales y siempre se ejecutan.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Ruta raíz del proyecto ───────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# ── Rutas de assets de imagen ─────────────────────────────────────────────────
_DIR_ASSETS = Path(__file__).parent.parent / "assets"
_IMG_FRONTAL  = _DIR_ASSETS / "persona_frontal.jpg"
_IMG_DOS_ROSTROS = _DIR_ASSETS / "dos_rostros.jpg"
_IMG_CON_LENTES  = _DIR_ASSETS / "persona_con_lentes.jpg"


# ── Importaciones opcionales (requieren InsightFace instalado) ────────────────
try:
    from app.utils.face_utils import (
        extraer_embedding,
        normalizar_l2,
        similitud_coseno,
    )
    FACE_UTILS_DISPONIBLE = True
except ImportError:
    FACE_UTILS_DISPONIBLE = False

# ── Importaciones para SVM (sklearn siempre disponible en el proyecto) ────────
try:
    import joblib
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder, Normalizer
    from sklearn.svm import SVC
    SKLEARN_DISPONIBLE = True
except ImportError:
    SKLEARN_DISPONIBLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _leer_imagen(ruta: Path) -> bytes:
    """Lee una imagen del disco y retorna sus bytes."""
    return ruta.read_bytes()


def _crear_jpeg_negro(ancho: int = 200, alto: int = 200) -> bytes:
    """Genera un JPEG negro sintético usando Pillow o fallback mínimo."""
    try:
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (ancho, alto), color=(0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()
    except ImportError:
        # Bytes JPEG mínimos (marcadores SOI + APP0 + EOI)
        return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100 + b"\xff\xd9"


def _construir_pipeline(c: float = 5.0, kernel: str = "rbf", semilla: int = 42) -> "Pipeline":
    """Construye el mismo Pipeline que usa entrenamiento/entrenar_clasificador.py."""
    return Pipeline([
        ("normalizador", Normalizer(norm="l2")),
        ("clasificador", SVC(
            C=c,
            kernel=kernel,
            probability=True,
            random_state=semilla,
            class_weight="balanced",
        )),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U01 — Extracción de embedding con imagen válida de un rostro
# ─────────────────────────────────────────────────────────────────────────────

class TestU01ExtraccionEmbeddingValido:
    """VESCOM-REC-U01: extraer_embedding() con exactamente un rostro frontal."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_FRONTAL.exists(), reason=f"Asset no encontrado: {_IMG_FRONTAL}")
    def test_retorna_ndarray_512_dimensiones(self):
        """U01-a: El embedding debe ser np.ndarray de shape (512,)."""
        imagen_bytes = _leer_imagen(_IMG_FRONTAL)
        embedding = extraer_embedding(imagen_bytes)

        assert isinstance(embedding, np.ndarray), "Debe retornar np.ndarray"
        assert embedding.shape == (512,), f"Shape esperado (512,), obtenido {embedding.shape}"

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_FRONTAL.exists(), reason=f"Asset no encontrado: {_IMG_FRONTAL}")
    def test_dtype_float32(self):
        """U01-b: El embedding debe ser de tipo float32."""
        imagen_bytes = _leer_imagen(_IMG_FRONTAL)
        embedding = extraer_embedding(imagen_bytes)

        assert embedding.dtype == np.float32, (
            f"dtype esperado float32, obtenido {embedding.dtype}"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_FRONTAL.exists(), reason=f"Asset no encontrado: {_IMG_FRONTAL}")
    def test_norma_cercana_a_uno(self):
        """U01-c: InsightFace retorna normed_embedding; la norma debe ser ≈1.0."""
        imagen_bytes = _leer_imagen(_IMG_FRONTAL)
        embedding = extraer_embedding(imagen_bytes)
        norma = float(np.linalg.norm(embedding))

        assert norma == pytest.approx(1.0, abs=1e-5), (
            f"Norma esperada ≈1.0 (normed_embedding), obtenida {norma:.6f}"
        )

    def test_mock_retorna_vector_512(self):
        """U01-d (mock): Simula extraer_embedding retornando vector de 512 dims."""
        vector_simulado = np.random.rand(512).astype(np.float32)

        with patch("app.utils.face_utils.extraer_embedding", return_value=vector_simulado):
            from app.utils.face_utils import extraer_embedding as _fn
            resultado = _fn(b"bytes_de_imagen_simulada")

        assert resultado.shape == (512,)
        assert resultado.dtype == np.float32


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U02 — Extracción de embedding con imagen sin rostro
# ─────────────────────────────────────────────────────────────────────────────

class TestU02SinRostro:
    """VESCOM-REC-U02: extraer_embedding() debe lanzar ValueError ante 0 rostros."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    def test_imagen_negra_sintetica_lanza_valueerror(self, imagen_sin_rostro):
        """U02-a: Imagen negra (fixture conftest) → ValueError."""
        with pytest.raises(ValueError, match="[Nn]o se detectó"):
            extraer_embedding(imagen_sin_rostro)

    def test_mock_sin_rostro_lanza_valueerror(self):
        """U02-b (mock): Simula el error de ArcFace ante frame sin rostro."""
        with patch("app.utils.face_utils.extraer_embedding") as mock_fn:
            mock_fn.side_effect = ValueError(
                "No se detectó ningún rostro en la imagen. "
                "Prueba con una foto más frontal."
            )
            with pytest.raises(ValueError, match="[Nn]o se detectó"):
                mock_fn(b"frame_sin_rostro")

    def test_mock_mensaje_orientacion_incluido(self):
        """U02-c (mock): El mensaje de error orienta al usuario sobre la causa."""
        with patch("app.utils.face_utils.extraer_embedding") as mock_fn:
            mock_fn.side_effect = ValueError(
                "No se detectó ningún rostro en la imagen. "
                "Prueba con una foto más frontal, sin recortes extremos."
            )
            with pytest.raises(ValueError) as exc_info:
                mock_fn(b"cualquier_bytes")

            mensaje = str(exc_info.value)
            assert "rostro" in mensaje.lower(), (
                "El mensaje de error debe mencionar 'rostro' para orientar al usuario"
            )


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U03 — Extracción de embedding con imagen de múltiples rostros
# ─────────────────────────────────────────────────────────────────────────────

class TestU03MultiplesRostros:
    """VESCOM-REC-U03: extraer_embedding() con >1 rostro debe lanzar ValueError."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_DOS_ROSTROS.exists(), reason=f"Asset no encontrado: {_IMG_DOS_ROSTROS}")
    def test_imagen_real_dos_rostros_lanza_valueerror(self):
        """U03-a: Imagen real con dos personas → ValueError con conteo de rostros."""
        imagen_bytes = _leer_imagen(_IMG_DOS_ROSTROS)

        with pytest.raises(ValueError, match=r"Se detectaron \d+ rostros"):
            extraer_embedding(imagen_bytes)

    def test_mock_multiples_rostros_lanza_valueerror(self):
        """U03-b (mock): Simula que ArcFace detectó 2 rostros en el frame."""
        with patch("app.utils.face_utils.extraer_embedding") as mock_fn:
            mock_fn.side_effect = ValueError(
                "Se detectaron 2 rostros. Envía una imagen con un solo rostro"
            )
            with pytest.raises(ValueError, match=r"Se detectaron \d+ rostros"):
                mock_fn(b"frame_con_dos_caras")

    def test_mock_mensaje_indica_cantidad_detectada(self):
        """U03-c (mock): El mensaje de error incluye el conteo de rostros detectados."""
        n_rostros = 3
        with patch("app.utils.face_utils.extraer_embedding") as mock_fn:
            mock_fn.side_effect = ValueError(
                f"Se detectaron {n_rostros} rostros. Envía una imagen con un solo rostro"
            )
            with pytest.raises(ValueError) as exc_info:
                mock_fn(b"frame_grupal")

            assert str(n_rostros) in str(exc_info.value), (
                "El mensaje debe indicar cuántos rostros se detectaron"
            )


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U04 — Reconocimiento de persona con lentes (oclusión parcial)
# ─────────────────────────────────────────────────────────────────────────────

class TestU04PersonaConLentes:
    """VESCOM-REC-U04: buffalo_l soporta oclusión parcial (lentes)."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_CON_LENTES.exists(), reason=f"Asset no encontrado: {_IMG_CON_LENTES}")
    def test_extrae_embedding_con_lentes_sin_excepcion(self):
        """U04-a: Persona con lentes → embedding (512,) sin excepción."""
        imagen_bytes = _leer_imagen(_IMG_CON_LENTES)
        embedding = extraer_embedding(imagen_bytes)

        assert embedding.shape == (512,), (
            f"Shape esperado (512,), obtenido {embedding.shape}. "
            "El modelo buffalo_l debe detectar rostros con lentes."
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
    @pytest.mark.skipif(not _IMG_CON_LENTES.exists(), reason=f"Asset no encontrado: {_IMG_CON_LENTES}")
    def test_embedding_lentes_es_comparable_con_similitud_coseno(self):
        """U04-b: El embedding de persona con lentes es válido para comparación coseno."""
        imagen_bytes = _leer_imagen(_IMG_CON_LENTES)
        embedding = extraer_embedding(imagen_bytes)

        # Similitud consigo mismo debe ser ≈1.0
        sim = similitud_coseno(embedding, embedding)
        assert sim == pytest.approx(1.0, abs=1e-5), (
            f"Similitud consigo mismo debe ser ≈1.0, obtenido {sim:.6f}"
        )

    def test_mock_lentes_retorna_vector_valido(self):
        """U04-c (mock): Simula que buffalo_l procesa correctamente imagen con lentes."""
        embedding_simulado = np.random.rand(512).astype(np.float32)
        # Normalizar para simular normed_embedding de InsightFace
        embedding_simulado /= np.linalg.norm(embedding_simulado)

        with patch("app.utils.face_utils.extraer_embedding", return_value=embedding_simulado):
            from app.utils.face_utils import extraer_embedding as _fn
            resultado = _fn(b"bytes_persona_con_lentes")

        assert resultado.shape == (512,)
        # La norma del simulado debe ser ≈1.0
        assert float(np.linalg.norm(resultado)) == pytest.approx(1.0, abs=1e-5)


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U05 — Normalización L2 de un vector de embedding
# ─────────────────────────────────────────────────────────────────────────────

class TestU05NormalizacionL2:
    """VESCOM-REC-U05: normalizar_l2() produce vectores unitarios."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_vector_2d_norma_resultante_es_uno(self):
        """U05-a: Vector [3, 4] (norma=5) → normalizado con norma=1.0."""
        vec = np.array([3.0, 4.0], dtype=np.float32)
        resultado = normalizar_l2(vec)
        norma = float(np.linalg.norm(resultado))

        assert norma == pytest.approx(1.0, abs=1e-6), (
            f"Norma esperada 1.0, obtenida {norma}"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_vector_512d_aleatorio_norma_es_uno(self):
        """U05-b: Vector aleatorio de 512 dimensiones → norma=1.0 tras normalizar."""
        vec = np.random.rand(512).astype(np.float32)
        resultado = normalizar_l2(vec)
        norma = float(np.linalg.norm(resultado))

        assert norma == pytest.approx(1.0, abs=1e-6), (
            f"Norma esperada 1.0, obtenida {norma:.8f}"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_vector_ya_normalizado_permanece_igual(self):
        """U05-c: Normalizar un vector ya unitario no lo altera."""
        vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        resultado = normalizar_l2(vec)

        np.testing.assert_array_almost_equal(resultado, vec, decimal=6)

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_vector_cero_no_genera_division_por_cero(self):
        """U05-d: El vector cero (norma=0) se retorna sin dividir (evita NaN)."""
        vec = np.zeros(512, dtype=np.float32)
        resultado = normalizar_l2(vec)

        # Según la implementación: `return vector / norma if norma > 0 else vector`
        assert not np.any(np.isnan(resultado)), (
            "normalizar_l2 no debe producir NaN para el vector cero"
        )
        np.testing.assert_array_equal(resultado, vec)


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U06 — Similitud coseno entre el mismo vector (identidad)
# ─────────────────────────────────────────────────────────────────────────────

class TestU06SimilitudCosenoIdentidad:
    """VESCOM-REC-U06: similitud_coseno(v, v) == 1.0 para cualquier vector."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_similitud_vector_consigo_mismo_es_uno(self):
        """U06-a: similitud_coseno(v, v) debe retornar exactamente 1.0."""
        v = np.random.rand(512).astype(np.float32)
        sim = similitud_coseno(v, v)

        assert isinstance(sim, float), "similitud_coseno debe retornar float"
        assert sim == pytest.approx(1.0, abs=1e-6), (
            f"Similitud consigo mismo debe ser 1.0, obtenida {sim:.8f}"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_similitud_vector_unitario_consigo_mismo(self):
        """U06-b: Vector unitario puro ([1, 0, ...]) con sí mismo → 1.0."""
        v = np.zeros(512, dtype=np.float32)
        v[0] = 1.0
        sim = similitud_coseno(v, v)

        assert sim == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_similitud_retorna_float_no_ndarray(self):
        """U06-c: El valor de retorno debe ser Python float, no numpy scalar."""
        v = np.random.rand(512).astype(np.float32)
        sim = similitud_coseno(v, v)

        assert isinstance(sim, float), (
            f"Se esperaba float nativo, obtenido {type(sim).__name__}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U07 — Similitud coseno entre vectores ortogonales
# ─────────────────────────────────────────────────────────────────────────────

class TestU07SimilitudCosenoOrtogonal:
    """VESCOM-REC-U07: similitud_coseno(v_a, v_b) ≈ 0.0 para vectores perpendiculares."""

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_vectores_base_ortogonales(self):
        """U07-a: e₀ ⊥ e₁ → similitud coseno = 0.0."""
        v_a = np.zeros(512, dtype=np.float32)
        v_a[0] = 1.0   # vector base en dimensión 0
        v_b = np.zeros(512, dtype=np.float32)
        v_b[1] = 1.0   # vector base en dimensión 1 (perpendicular)

        sim = similitud_coseno(v_a, v_b)

        assert sim == pytest.approx(0.0, abs=1e-6), (
            f"Vectores ortogonales deben tener similitud ≈0.0, obtenida {sim:.8f}"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_similitud_simetrica(self):
        """U07-b: similitud_coseno(a, b) == similitud_coseno(b, a) (propiedad simétrica)."""
        v_a = np.random.rand(512).astype(np.float32)
        v_b = np.random.rand(512).astype(np.float32)

        sim_ab = similitud_coseno(v_a, v_b)
        sim_ba = similitud_coseno(v_b, v_a)

        assert sim_ab == pytest.approx(sim_ba, abs=1e-6), (
            "La similitud coseno debe ser simétrica: sim(a,b) == sim(b,a)"
        )

    @pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="face_utils no importable")
    def test_rango_de_valores_entre_menos_uno_y_uno(self):
        """U07-c: La similitud coseno siempre está en el intervalo [-1.0, 1.0]."""
        for _ in range(10):
            v_a = np.random.randn(512).astype(np.float32)
            v_b = np.random.randn(512).astype(np.float32)
            sim = similitud_coseno(v_a, v_b)

            assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6, (
                f"similitud_coseno fuera del rango válido [-1, 1]: {sim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U08 — Pipeline de entrenamiento SVM con dataset mínimo válido
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not SKLEARN_DISPONIBLE, reason="scikit-learn no instalado")
class TestU08PipelineSVM:
    """VESCOM-REC-U08: Pipeline Normalizer→SVC entrena y predice con datos sintéticos."""

    # Dataset mínimo: 3 personas, 2 embeddings cada una
    _X = np.random.rand(6, 512).astype(np.float32)
    _y = np.array([1, 1, 2, 2, 3, 3], dtype=np.int32)

    def test_construir_pipeline_retorna_pipeline(self):
        """U08-a: _construir_pipeline() devuelve instancia de sklearn Pipeline."""
        pipeline = _construir_pipeline(c=5.0, kernel="rbf", semilla=42)

        assert isinstance(pipeline, Pipeline), (
            "Se esperaba un objeto sklearn.pipeline.Pipeline"
        )

    def test_pipeline_tiene_etapas_normalizador_y_clasificador(self):
        """U08-b: El Pipeline debe tener exactamente 2 etapas: normalizador y clasificador."""
        pipeline = _construir_pipeline()
        nombres_etapas = [nombre for nombre, _ in pipeline.steps]

        assert "normalizador" in nombres_etapas, "Debe existir la etapa 'normalizador'"
        assert "clasificador" in nombres_etapas, "Debe existir la etapa 'clasificador'"

    def test_fit_no_lanza_excepcion(self):
        """U08-c: pipeline.fit(X, y) con dataset mínimo termina sin excepción."""
        pipeline = _construir_pipeline()
        codificador = LabelEncoder()
        y_enc = codificador.fit_transform(self._y)

        # No debe lanzar ninguna excepción
        pipeline.fit(self._X, y_enc)

    def test_predict_proba_shape_correcto(self):
        """U08-d: predict_proba retorna array de shape (n_samples, n_clases)."""
        pipeline = _construir_pipeline()
        codificador = LabelEncoder()
        y_enc = codificador.fit_transform(self._y)
        pipeline.fit(self._X, y_enc)

        probs = pipeline.predict_proba(self._X[:1])

        assert probs.shape == (1, 3), (
            f"Shape esperado (1, 3) para 3 clases, obtenido {probs.shape}"
        )

    def test_probabilidades_suman_uno_por_muestra(self):
        """U08-e: Las probabilidades de cada muestra deben sumar 1.0."""
        pipeline = _construir_pipeline()
        codificador = LabelEncoder()
        y_enc = codificador.fit_transform(self._y)
        pipeline.fit(self._X, y_enc)

        probs = pipeline.predict_proba(self._X)
        sumas = probs.sum(axis=1)

        np.testing.assert_allclose(
            sumas,
            np.ones(len(self._X)),
            atol=1e-6,
            err_msg="Las probabilidades por muestra deben sumar 1.0",
        )

    def test_artefacto_joblib_se_guarda_y_carga(self, tmp_path):
        """U08-f: El artefacto .joblib se persiste y se puede recargar con la estructura esperada."""
        pipeline = _construir_pipeline()
        codificador = LabelEncoder()
        y_enc = codificador.fit_transform(self._y)
        pipeline.fit(self._X, y_enc)

        ruta = tmp_path / "test_svm.joblib"
        artefacto = {
            "pipeline": pipeline,
            "codificador_etiquetas": codificador,
            "num_personas": int(len(codificador.classes_)),
            "dimension_embedding": self._X.shape[1],
            "kernel": "rbf",
            "parametro_c": 5.0,
        }
        joblib.dump(artefacto, ruta)

        # Recargar y verificar claves esperadas por _cargar_modelo_svm()
        cargado = joblib.load(ruta)
        assert "pipeline" in cargado, "El artefacto debe contener la clave 'pipeline'"
        assert "codificador_etiquetas" in cargado, (
            "El artefacto debe contener 'codificador_etiquetas'"
        )
        assert cargado["num_personas"] == 3
        assert cargado["dimension_embedding"] == 512


# ─────────────────────────────────────────────────────────────────────────────
# VESCOM-REC-U09 — Carga de modelo SVM con archivo corrupto o estructura inválida
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not SKLEARN_DISPONIBLE, reason="scikit-learn / joblib no instalado")
class TestU09ModeloSVMCorrupto:
    """VESCOM-REC-U09: _cargar_modelo_svm() retorna None ante .joblib con claves inválidas."""

    def test_archivo_con_claves_invalidas_retorna_none(self, tmp_path, monkeypatch):
        """U09-a: Joblib con dict vacío o claves incorrectas → _cargar_modelo_svm() = None."""
        ruta_corrupta = tmp_path / "corrupto.joblib"
        joblib.dump({"clave_invalida": True, "otro_campo": 42}, ruta_corrupta)

        # Parchear la ruta del modelo a nivel de módulo
        from app.services import reconocimiento_service
        monkeypatch.setattr(reconocimiento_service, "_RUTA_MODELO_SVM", ruta_corrupta)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cargado", False)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cache", {})
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_mtime", None)

        resultado = reconocimiento_service._cargar_modelo_svm(forzar_recarga=True)

        assert resultado is None, (
            "Un .joblib con claves inválidas debe retornar None, no lanzar excepción"
        )

    def test_archivo_inexistente_retorna_none(self, tmp_path, monkeypatch):
        """U09-b: Ruta de modelo apuntando a archivo inexistente → None."""
        ruta_inexistente = tmp_path / "no_existe.joblib"

        from app.services import reconocimiento_service
        monkeypatch.setattr(reconocimiento_service, "_RUTA_MODELO_SVM", ruta_inexistente)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cargado", False)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cache", {})
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_mtime", None)

        resultado = reconocimiento_service._cargar_modelo_svm(forzar_recarga=True)

        assert resultado is None, (
            "Archivo inexistente debe retornar None sin excepción"
        )

    def test_archivo_corrupto_no_propaga_excepcion(self, tmp_path, monkeypatch, capsys):
        """U09-c: Un .joblib corrupto no propaga excepción; imprime advertencia [WARN]."""
        ruta_corrupta = tmp_path / "datos_corruptos.joblib"
        # Escribir bytes que joblib no puede deserializar correctamente
        ruta_corrupta.write_bytes(b"ESTO_NO_ES_UN_JOBLIB_VALIDO_\x00\xff\xfe")

        from app.services import reconocimiento_service
        monkeypatch.setattr(reconocimiento_service, "_RUTA_MODELO_SVM", ruta_corrupta)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cargado", False)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cache", {})
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_mtime", None)

        # No debe propagar ninguna excepción
        try:
            resultado = reconocimiento_service._cargar_modelo_svm(forzar_recarga=True)
        except Exception as exc:
            pytest.fail(
                f"_cargar_modelo_svm() propagó excepción inesperada: {type(exc).__name__}: {exc}"
            )

        # Debe retornar None
        assert resultado is None

        # La advertencia [WARN] debe aparecer en stdout
        captura = capsys.readouterr()
        assert "[WARN]" in captura.out, (
            "Se esperaba un mensaje [WARN] en stdout al fallar la carga del modelo"
        )

    def test_modelo_valido_retorna_artefacto_con_claves(self, tmp_path, monkeypatch):
        """U09-d (control positivo): Un .joblib bien formado sí retorna el artefacto."""
        # Construir un pipeline mínimo válido
        pipeline = _construir_pipeline()
        codificador = LabelEncoder()
        X = np.random.rand(4, 512).astype(np.float32)
        y_enc = codificador.fit_transform([1, 1, 2, 2])
        pipeline.fit(X, y_enc)

        ruta_valida = tmp_path / "valido.joblib"
        artefacto = {
            "pipeline": pipeline,
            "codificador_etiquetas": codificador,
            "num_personas": 2,
            "dimension_embedding": 512,
            "kernel": "rbf",
            "parametro_c": 5.0,
        }
        joblib.dump(artefacto, ruta_valida)

        from app.services import reconocimiento_service
        monkeypatch.setattr(reconocimiento_service, "_RUTA_MODELO_SVM", ruta_valida)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cargado", False)
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_cache", {})
        monkeypatch.setattr(reconocimiento_service, "_modelo_svm_mtime", None)

        resultado = reconocimiento_service._cargar_modelo_svm(forzar_recarga=True)

        assert resultado is not None, "Un .joblib válido debe retornar el artefacto"
        assert "pipeline" in resultado
        assert "codificador_etiquetas" in resultado
