"""Definiciones de workflows por dominio.

Cada Workflow describe qué arquitectura usar, qué entidades sugerir
y qué características adicionales activar cuando se detecta un dominio.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Workflow:
    domain: str
    display_name: str
    description: str
    architecture: str                          # "hexagonal" | "etl"
    suggested_entities: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    notes: str = ""


WORKFLOWS: dict[str, Workflow] = {
    "health": Workflow(
        domain="health",
        display_name="Salud / Epidemiología",
        description="Sistemas clínicos, epidemiológicos o de salud pública",
        architecture="hexagonal",
        suggested_entities=["paciente", "diagnostico", "medicamento", "cita", "resultado"],
        features=["audit_log", "soft_delete", "gdpr"],
        notes="Se recomienda tabla de auditoría y borrado lógico por normativa de datos sensibles.",
    ),
    "finance": Workflow(
        domain="finance",
        display_name="Finanzas / Portfolio",
        description="Transacciones, cuentas, portfolio de inversión y métricas de riesgo",
        architecture="hexagonal",
        suggested_entities=[
            "cuenta", "transaccion", "factura", "pago", "balance",
            "activo", "posicion", "riesgo_metrica", "rebalanceo",
        ],
        features=["audit_log", "immutable_records", "double_entry", "time_series"],
        notes=(
            "Registros inmutables (immutable_records). Para portfolio: Posicion = estado actual "
            "de cada activo; Transaccion = movimientos; RiesgoMetrica = VaR/Sharpe/drawdown. "
            "time_series para NAV diario y precios históricos."
        ),
    ),
    "logistics": Workflow(
        domain="logistics",
        display_name="Logística / Delivery",
        description="Gestión de rutas, pedidos, repartidores y tracking",
        architecture="hexagonal",
        suggested_entities=["cliente", "repartidor", "pedido", "ruta", "asignacion", "historial_estado"],
        features=["state_machine", "audit_log"],
        notes="Los pedidos siguen una máquina de estados. Se recomienda tabla de historial de estados.",
    ),
    "ecommerce": Workflow(
        domain="ecommerce",
        display_name="E-Commerce",
        description="Catálogo, órdenes, pagos y gestión de inventario",
        architecture="hexagonal",
        suggested_entities=["producto", "categoria", "orden", "cliente", "pago", "inventario"],
        features=["state_machine", "soft_delete", "audit_log"],
        notes="Las órdenes y pagos requieren trazabilidad completa.",
    ),
    "education": Workflow(
        domain="education",
        display_name="Educación",
        description="Gestión académica: cursos, estudiantes, calificaciones",
        architecture="etl",
        suggested_entities=["estudiante", "curso", "profesor", "inscripcion", "calificacion"],
        features=["soft_delete"],
        notes="",
    ),
    "climate": Workflow(
        domain="climate",
        display_name="Clima / Medioambiente",
        description="Datos ambientales, estaciones meteorológicas, emisiones",
        architecture="etl",
        suggested_entities=["estacion", "medicion", "contaminante", "region", "reporte"],
        features=["time_series"],
        notes="Los datos climáticos son mayormente series de tiempo. Se recomienda arquitectura ETL.",
    ),
    "social_science": Workflow(
        domain="social_science",
        display_name="Ciencias Sociales",
        description="Encuestas, demografía, análisis socioeconómico",
        architecture="etl",
        suggested_entities=["encuesta", "respuesta", "indicador", "region", "periodo"],
        features=["time_series"],
        notes="",
    ),
    "bioinformatics": Workflow(
        domain="bioinformatics",
        display_name="Bioinformática / Omics",
        description="Pipelines de análisis genómico, proteómico, metabolómico y metagenómico",
        architecture="etl",
        suggested_entities=[
            "muestra", "run_secuenciacion", "variante", "gen",
            "resultado_analisis", "pipeline_ejecucion",
        ],
        features=["time_series", "audit_log"],
        notes=(
            "Datos moleculares en pipeline (FASTQ→BAM→VCF→anotación); matrices de expresión "
            "(HDF5/Parquet). Trazabilidad de ejecuciones (pipeline_ejecucion) y versionado "
            "de referencias genómicas son críticos para reproducibilidad computacional."
        ),
    ),
    "generic": Workflow(
        domain="generic",
        display_name="Genérico / ETL",
        description="Pipeline de datos genérico sin dominio específico",
        architecture="etl",
        suggested_entities=["fuente", "registro", "reporte"],
        features=[],
        notes="",
    ),
}

ARCHITECTURE_DESCRIPTIONS = {
    "hexagonal": "Hexagonal (ports & adapters) — domain / application / infrastructure",
    "etl":       "ETL pipeline — sources / transforms / repositories / pipelines",
    "ml":        "ML Pipeline — ETL + features / models / evaluation / training + inference",
}


def get_workflow(domain: str) -> Workflow:
    from dataforge.core.plugins import get_registry
    registry = get_registry()
    if domain in registry.domains:
        pd = registry.domains[domain]
        return Workflow(
            domain=pd.key,
            display_name=pd.display_name,
            description=pd.description,
            architecture=pd.architecture,
            suggested_entities=pd.suggested_entities,
            features=pd.features,
            notes=pd.notes,
        )
    return WORKFLOWS.get(domain, WORKFLOWS["generic"])


def get_all_workflows() -> dict[str, Workflow]:
    from dataforge.core.plugins import get_registry
    registry = get_registry()
    merged = dict(WORKFLOWS)
    for pd in registry.domains.values():
        merged[pd.key] = Workflow(
            domain=pd.key,
            display_name=pd.display_name,
            description=pd.description,
            architecture=pd.architecture,
            suggested_entities=pd.suggested_entities,
            features=pd.features,
            notes=pd.notes,
        )
    return merged


def get_all_architectures() -> dict[str, str]:
    from dataforge.core.plugins import get_registry
    registry = get_registry()
    merged = dict(ARCHITECTURE_DESCRIPTIONS)
    for pa in registry.architectures.values():
        merged[pa.key] = pa.description
    return merged


def list_workflows() -> list[Workflow]:
    return list(get_all_workflows().values())
