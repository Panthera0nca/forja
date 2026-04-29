"""Clasificador de dominio para proyectos DataForge.

Perceptrón multicapa (sklearn MLPClassifier) entrenado sobre keywords por dominio.
Se entrena en el primer uso (~200ms) y queda cacheado en memoria para la sesión.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------------
# Datos de entrenamiento: (texto de keywords, dominio)
# ---------------------------------------------------------------------------

_TRAINING: list[tuple[str, str]] = [
    # health
    ("paciente diagnostico medicamento doctor hospital cita", "health"),
    ("enfermedad tratamiento clinica vacuna dosis farmacia", "health"),
    ("covid epidemia sintoma laboratorio resultado prueba", "health"),
    ("prescripcion consulta medico historia clinica salud", "health"),
    ("triage urgencia emergencia quirofano cirugia enfermero", "health"),
    ("epidemiologia mortalidad morbilidad incidencia prevalencia", "health"),
    ("patient diagnosis medication doctor hospital appointment", "health"),
    ("disease treatment clinic vaccine dose pharmacy", "health"),

    # finance
    ("transaccion cuenta pago factura deuda credito", "finance"),
    ("inversion banco dinero presupuesto balance activo", "finance"),
    ("ledger pasivo patrimonio impuesto declaracion gasto", "finance"),
    ("bolsa accion dividendo portafolio mercado fondo", "finance"),
    ("prestamo hipoteca cuota amortizacion interes tasa", "finance"),
    ("contabilidad auditoria balance general estado financiero", "finance"),
    ("transaction payment invoice credit bank investment", "finance"),
    ("accounting ledger balance asset liability equity", "finance"),

    # logistics
    ("entrega ruta repartidor pedido envio paquete", "logistics"),
    ("tracking flota conductor almacen inventario bodega", "logistics"),
    ("despacho transporte distribucion carga flete costo", "logistics"),
    ("delivery order pickup warehouse fleet driver route", "logistics"),
    ("asignacion zona cobertura cliente destino origen", "logistics"),
    ("last mile shipment carrier dispatch logistics chain", "logistics"),

    # ecommerce
    ("producto carrito orden cliente inventario tienda", "ecommerce"),
    ("descuento precio categoria proveedor catalogo stock", "ecommerce"),
    ("checkout compra venta reseña rating vendedor", "ecommerce"),
    ("marketplace cupon promocion devolución reembolso pago", "ecommerce"),
    ("product cart order customer inventory store discount", "ecommerce"),
    ("seller buyer listing shipping return refund coupon", "ecommerce"),

    # education
    ("estudiante curso profesor calificacion materia aula", "education"),
    ("examen horario inscripcion nota grado universidad", "education"),
    ("colegio tarea tesis asignatura practica diploma", "education"),
    ("student course teacher grade subject classroom exam", "education"),
    ("enrollment schedule assignment syllabus curriculum", "education"),
    ("learning module quiz certification training e-learning", "education"),

    # climate
    ("temperatura precipitacion clima estacion meteorologica", "climate"),
    ("emision contaminante aire calidad ambiente sensor", "climate"),
    ("energia renovable solar viento hidrica carbono", "climate"),
    ("ecosistema biodiversidad especie habitat recurso", "climate"),
    ("temperature rainfall weather station forecast", "climate"),
    ("emission pollution air quality sensor carbon footprint", "climate"),

    # social_science
    ("encuesta poblacion demografico estadistica social", "social_science"),
    ("votacion eleccion partido politica gobierno censo", "social_science"),
    ("crimen delito seguridad policia incidente reporte", "social_science"),
    ("salario empleo desempleo trabajo empresa laboral", "social_science"),
    ("survey population demographic statistic social", "social_science"),
    ("election vote crime employment inequality poverty", "social_science"),

    # bioinformatics
    ("secuencia gen genoma cromosoma mutacion variante alineamiento", "bioinformatics"),
    ("genomics sequencing variant calling alignment FASTQ VCF BAM reference genome", "bioinformatics"),
    ("proteina metabolito expresion genica transcriptoma omics", "bioinformatics"),
    ("proteomics mass spectrometry peptide protein fold change quantification", "bioinformatics"),
    ("metabolomica metabolito via metabolica KEGG cromatografia NMR espectroscopia", "bioinformatics"),
    ("metabolomics metabolite pathway GC-MS LC-MS NMR spectroscopy", "bioinformatics"),
    ("metagenómica microbioma 16S diversidad alpha beta OTU abundancia amplicon", "bioinformatics"),
    ("rna-seq chip-seq atac-seq single-cell scRNA expresion diferencial pipeline nextflow", "bioinformatics"),

    # generic / etl
    ("data pipeline etl fuente transformacion ingesta", "generic"),
    ("analisis reporte dashboard metricas kpi extraccion", "generic"),
    ("procesamiento carga batch streaming ingenieria datos", "generic"),
    ("data pipeline source transform load batch stream", "generic"),
    ("analytics report metrics dashboard warehouse lake", "generic"),
]

# ---------------------------------------------------------------------------
# Construcción del clasificador
# ---------------------------------------------------------------------------

_pipeline: "Pipeline | None" = None


def _normalize(text: str) -> str:
    """Normaliza el texto: underscores → espacios, minúsculas."""
    import re
    text = re.sub(r"[_\-/]", " ", text)
    return text.lower().strip()


def _build() -> "Pipeline":
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline

    training = list(_TRAINING)

    # Agregar keywords de plugins instalados
    try:
        from dataforge.core.plugins import get_registry
        for domain in get_registry().domains.values():
            if domain.keywords:
                training.append((" ".join(domain.keywords), domain.key))
    except Exception:
        pass

    texts, labels = zip(*training)
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            preprocessor=_normalize,
        )),
        ("mlp", MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            max_iter=1000,
            random_state=42,
        )),
    ])
    clf.fit(list(texts), list(labels))
    return clf


def _get() -> "Pipeline":
    global _pipeline
    if _pipeline is None:
        _pipeline = _build()
    return _pipeline


def reset_pipeline() -> None:
    """Fuerza reconstrucción del clasificador (útil si se instalan plugins en runtime)."""
    global _pipeline
    _pipeline = None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

DOMAINS = [
    "health",
    "finance",
    "logistics",
    "ecommerce",
    "education",
    "climate",
    "social_science",
    "bioinformatics",
    "generic",
]


def classify(text: str) -> tuple[str, float]:
    """Clasifica texto libre → (dominio, confianza 0-1)."""
    clf = _get()
    proba = clf.predict_proba([_normalize(text)])[0]
    idx = int(proba.argmax())
    return str(clf.classes_[idx]), float(proba[idx])


def top_domains(text: str, n: int = 3) -> list[tuple[str, float]]:
    """Retorna los n dominios más probables con sus scores."""
    clf = _get()
    proba = clf.predict_proba([_normalize(text)])[0]
    pairs = sorted(zip(clf.classes_, proba), key=lambda x: x[1], reverse=True)
    return [(str(d), float(s)) for d, s in pairs[:n]]
