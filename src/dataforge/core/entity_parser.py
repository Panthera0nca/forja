"""Parser de definiciones de entidades en texto plano.

Acepta:  "Cliente (id, nombre, dirección, teléfono)"
         "pedido"                            ← solo nombre, sin campos
         "id, cliente_id, fecha, estado"     ← solo campos, sin nombre

Infiere tipos SQL y Python a partir de los nombres de los campos:
  nombre      → TEXT NOT NULL          / str
  telefono    → VARCHAR(20)            / str
  cliente_id  → INTEGER NOT NULL FK   / int
  fecha       → TIMESTAMP WITH TZ     / datetime
  estado      → TEXT + CHECK (enum)   / Literal[...]
  precio      → NUMERIC(12,2)         / Decimal
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Normalización de texto
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _to_snake(text: str) -> str:
    text = _strip_accents(text.lower().strip())
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "campo"


def _to_pascal(snake: str) -> str:
    return "".join(w.capitalize() for w in snake.split("_"))


def _pluralize(name: str) -> str:
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith(("s", "sh", "ch", "x", "z")):
        return name + "es"
    return name + "s"


# ---------------------------------------------------------------------------
# Enum values por (dominio, campo)
# ---------------------------------------------------------------------------

_ENUM_VALUES: dict[tuple[str, str], list[str]] = {
    ("logistics",     "estado"):    ["pendiente", "asignado", "en_camino", "entregado", "cancelado"],
    ("ecommerce",     "estado"):    ["pendiente", "procesando", "enviado", "entregado", "cancelado", "devuelto"],
    ("health",        "estado"):    ["activo", "inactivo", "en_tratamiento", "dado_de_alta", "fallecido"],
    ("finance",       "estado"):    ["pendiente", "aprobado", "rechazado", "completado", "revertido"],
    ("education",     "estado"):    ["inscrito", "cursando", "aprobado", "reprobado", "retirado"],
    ("*",             "estado"):    ["activo", "inactivo", "pendiente"],
    ("logistics",     "vehiculo"):  ["moto", "bicicleta", "carro", "camion", "furgoneta"],
    ("*",             "rol"):       ["admin", "usuario", "moderador", "invitado"],
    ("*",             "genero"):    ["masculino", "femenino", "otro", "prefiero_no_decir"],
    ("*",             "tipo"):      [],   # demasiado genérico → TEXT sin CHECK
    ("*",             "prioridad"): ["baja", "media", "alta", "critica"],
    ("*",             "moneda"):    ["COP", "USD", "EUR", "MXN", "BRL"],

    # bioinformatics
    ("bioinformatics", "estado"):          ["recibida", "en_proceso", "completada", "fallida", "archivada"],
    ("bioinformatics", "tipo"):            ["genomica", "transcriptomica", "proteomica", "metabolomica", "metagenómica"],
    ("bioinformatics", "plataforma"):      ["illumina", "nanopore", "pacbio", "ion_torrent", "bgiseq"],
    ("bioinformatics", "organismo"):       ["homo_sapiens", "mus_musculus", "e_coli", "arabidopsis", "otro"],
    ("bioinformatics", "estado_variante"): ["benigna", "probablemente_benigna", "vus", "probablemente_patogenica", "patogenica"],

    # finance — extensiones para portfolio
    ("finance", "tipo_activo"):  ["accion", "bono", "etf", "fondo_mutuo", "cripto", "divisa", "derivado"],
    ("finance", "tipo"):         ["compra", "venta", "dividendo", "transferencia", "comision", "rebalanceo"],
    ("finance", "estado_orden"): ["pendiente", "ejecutada", "cancelada", "parcial", "rechazada", "expirada"],
    ("finance", "moneda"):       ["COP", "USD", "EUR", "MXN", "BRL", "GBP", "JPY", "CHF"],
}


def _get_enum_values(field_name: str, domain: str) -> list[str]:
    return (
        _ENUM_VALUES.get((domain, field_name))
        or _ENUM_VALUES.get(("*", field_name))
        or []
    )


# ---------------------------------------------------------------------------
# Reglas de inferencia de tipos
# ---------------------------------------------------------------------------
# (pattern, sql_type, python_type, nullable, extra_import)
# Se evalúan en orden — la primera que encaje gana.

_RULES: list[tuple[str, str, str, bool, str | None]] = [
    # ── Identidad ──────────────────────────────────────────────────────────
    (r"^id$",
     "SERIAL PRIMARY KEY", "Optional[int]", True, None),

    # ── Llaves foráneas ─────────────────────────────────────────────────────
    (r"^.+_id$",
     "INTEGER NOT NULL", "int", False, None),

    # ── Nombre / texto corto ────────────────────────────────────────────────
    (r"^(nombre|name|titulo|title|apellido|primer_nombre|segundo_nombre"
     r"|firstname|lastname|fullname|razon_social)$",
     "TEXT NOT NULL", "str", False, None),

    # ── Descripción / texto largo ───────────────────────────────────────────
    (r"^(descripcion|description|detalle|detail|observacion|observation"
     r"|nota|notas|notes|comentario|comment|resumen|summary|contenido|content)$",
     "TEXT", "Optional[str]", True, None),

    # ── Dirección ───────────────────────────────────────────────────────────
    (r"^(direccion|address|domicilio|ubicacion|location)$",
     "TEXT NOT NULL", "str", False, None),

    # ── Contacto ────────────────────────────────────────────────────────────
    (r"^(telefono|phone|celular|mobile|tel|fax).*",
     "VARCHAR(20)", "str", False, None),
    (r"^(email|correo|mail).*|.*_(email|correo|mail)$",
     "VARCHAR(255)", "str", False, None),

    # ── Fechas y tiempos ────────────────────────────────────────────────────
    (r"^fecha$|^fecha_.+|.+_fecha$|^date$|^date_.+|.+_date$",
     "TIMESTAMP WITH TIME ZONE NOT NULL", "datetime", False, "datetime"),
    (r"^(created_at|updated_at|deleted_at|fecha_creacion|fecha_actualizacion)$",
     "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP", "Optional[datetime]", True, "datetime"),

    # ── Dinero / finanzas ───────────────────────────────────────────────────
    (r"^(precio|price|costo|cost|monto|amount|valor|value|total|subtotal"
     r"|salario|salary|sueldo|wage|ingreso|egreso|deuda|saldo|balance).*",
     "NUMERIC(12,2) NOT NULL", "Decimal", False, "Decimal"),
    (r"^(descuento|discount|tasa|rate|porcentaje|percentage|comision|commission).*",
     "NUMERIC(5,2)", "Optional[Decimal]", True, "Decimal"),

    # ── Estado / tipo / categoría → enum ────────────────────────────────────
    (r"^(estado|status)$",
     "TEXT NOT NULL", "str", False, None),           # manejado especialmente como enum
    (r"^(tipo|type|categoria|category|clase|class|modalidad|modalidad)$",
     "TEXT", "Optional[str]", True, None),            # puede ser enum

    # ── Booleanos ───────────────────────────────────────────────────────────
    (r"^(activo|active|habilitado|enabled|disponible|available|verificado"
     r"|verified|publicado|published|completado|completada|pagado|pagada"
     r"|leido|visto|favorito|archivado)$",
     "BOOLEAN NOT NULL DEFAULT TRUE", "bool", False, None),

    # ── Contadores / enteros ─────────────────────────────────────────────────
    (r"^(cantidad|quantity|count|numero|number|stock|capacidad|capacity"
     r"|intentos|attempts|orden|orden_).*|.*(count|total|cantidad)$",
     "INTEGER", "int", False, None),

    # ── Coordenadas / geografía ──────────────────────────────────────────────
    (r"^(latitud|lat|latitude)$",    "NUMERIC(10,7)", "Optional[float]", True, None),
    (r"^(longitud|lon|lng|longitude)$", "NUMERIC(10,7)", "Optional[float]", True, None),
    (r"^(distancia|distance).*|.*_km$",
     "NUMERIC(8,2)", "Optional[float]", True, None),

    # ── URLs / multimedia ────────────────────────────────────────────────────
    (r"^(url|imagen|image|foto|photo|avatar|logo|icono|icon|archivo|file"
     r"|documento|document|video|audio|thumbnail|banner).*",
     "TEXT", "Optional[str]", True, None),

    # ── Identificadores externos ─────────────────────────────────────────────
    (r"^(codigo|code|clave|key|referencia|reference|numero_doc|nit|cedula"
     r"|dni|rfc|uuid|slug|token|hash).*",
     "VARCHAR(100)", "str", False, None),

    # ── Peso / medidas ───────────────────────────────────────────────────────
    (r"^(peso|weight).*",  "NUMERIC(8,3)", "Optional[float]", True, None),
    (r"^(altura|height|ancho|width|largo|length|volumen|volume).*",
     "NUMERIC(8,2)", "Optional[float]", True, None),

    # ── Default ──────────────────────────────────────────────────────────────
    (r".*", "TEXT", "Optional[str]", True, None),
]

_COMPILED_RULES = [(re.compile(pat, re.IGNORECASE), *rest) for pat, *rest in _RULES]

# Campos que siempre se añaden automáticamente si no están en la definición
_AUTO_TIMESTAMPS = {"created_at", "updated_at"}

# Campos que NO son insertables/actualizables manualmente
_NON_INSERT = {"id", "created_at", "updated_at"}
_NON_UPDATE  = {"id", "created_at"}


# ---------------------------------------------------------------------------
# Dataclasses de salida
# ---------------------------------------------------------------------------

@dataclass
class FieldDef:
    name: str                        # snake_case, sin acentos
    sql_type: str                    # tipo SQL completo (ej: "TEXT NOT NULL")
    python_type: str                 # tipo Python (ej: "str", "Optional[int]")
    nullable: bool
    python_default: str | None       # valor por defecto en Python (ej: "None")
    sql_default: str | None          # valor por defecto en SQL
    extra_import: str | None         # módulo a importar (ej: "datetime")
    is_pk: bool = False
    is_fk: bool = False
    fk_table: str | None = None      # tabla referenciada (plural)
    is_enum: bool = False
    enum_values: list[str] = field(default_factory=list)
    enum_var: str | None = None      # nombre del Literal (ej: "EstadoPedido")
    comment: str | None = None


@dataclass
class EntityDef:
    raw_name: str
    snake_name: str
    class_name: str
    table_name: str
    fields: list[FieldDef]

    # Conjuntos derivados útiles para templates
    @property
    def pk_field(self) -> FieldDef | None:
        return next((f for f in self.fields if f.is_pk), None)

    @property
    def fk_fields(self) -> list[FieldDef]:
        return [f for f in self.fields if f.is_fk]

    @property
    def enum_fields(self) -> list[FieldDef]:
        return [f for f in self.fields if f.is_enum and f.enum_values]

    @property
    def insertable_fields(self) -> list[FieldDef]:
        return [f for f in self.fields if f.name not in _NON_INSERT]

    @property
    def updatable_fields(self) -> list[FieldDef]:
        return [f for f in self.fields if f.name not in _NON_UPDATE]

    @property
    def python_imports(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for f in self.fields:
            if f.extra_import and f.extra_import not in seen:
                seen.add(f.extra_import)
                result.append(f.extra_import)
        return result

    @property
    def needs_optional(self) -> bool:
        return any(f.nullable for f in self.fields)

    @property
    def needs_literal(self) -> bool:
        return bool(self.enum_fields)

    @property
    def needs_decimal(self) -> bool:
        return any(f.extra_import == "Decimal" for f in self.fields)


# ---------------------------------------------------------------------------
# Motor de inferencia
# ---------------------------------------------------------------------------

def _infer_field(name: str, domain: str = "generic") -> FieldDef:
    """Infiere un FieldDef completo a partir del nombre del campo."""
    clean = _to_snake(name)

    # Caso especial: id
    if clean == "id":
        return FieldDef(
            name="id", sql_type="SERIAL PRIMARY KEY",
            python_type="Optional[int]", nullable=True,
            python_default="None", sql_default=None,
            extra_import=None, is_pk=True,
        )

    # Caso especial: FK (*_id)
    if re.match(r"^.+_id$", clean):
        ref_entity = re.sub(r"_id$", "", clean)
        ref_table = _pluralize(ref_entity)
        return FieldDef(
            name=clean, sql_type="INTEGER NOT NULL",
            python_type="int", nullable=False,
            python_default=None, sql_default=None,
            extra_import=None, is_fk=True, fk_table=ref_table,
            comment=f"FK → {ref_table}",
        )

    # Caso especial: timestamps automáticos
    if clean in _AUTO_TIMESTAMPS:
        return FieldDef(
            name=clean,
            sql_type="TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
            python_type="Optional[datetime]", nullable=True,
            python_default="None", sql_default="CURRENT_TIMESTAMP",
            extra_import="datetime",
        )

    # Detección de enums
    enum_values = _get_enum_values(clean, domain)
    is_enum = bool(enum_values) or clean in ("estado", "status", "tipo", "type", "rol", "role")

    # Buscar tipo por reglas
    sql_type = "TEXT"
    python_type = "Optional[str]"
    nullable = True
    extra_import: str | None = None

    for compiled_re, s_type, p_type, null, imp in _COMPILED_RULES:
        if compiled_re.match(clean):
            sql_type = s_type
            python_type = p_type
            nullable = null
            extra_import = imp
            break

    # Ajustar para enums
    if is_enum and enum_values:
        enum_var = _to_pascal(clean) + "Type"
        values_str = ", ".join(f'"{v}"' for v in enum_values)
        check = f"CHECK ({clean} IN ({', '.join(repr(v) for v in enum_values)}))"
        # Añadir CHECK al tipo SQL
        if "NOT NULL" in sql_type:
            sql_type = sql_type.replace("NOT NULL", f"NOT NULL {check}")
        else:
            sql_type = f"{sql_type} {check}"
        python_type = enum_var
    else:
        enum_var = None
        enum_values = []

    python_default = "None" if nullable else None

    return FieldDef(
        name=clean,
        sql_type=sql_type,
        python_type=python_type,
        nullable=nullable,
        python_default=python_default,
        sql_default=None,
        extra_import=extra_import,
        is_enum=is_enum and bool(enum_values),
        enum_values=enum_values,
        enum_var=enum_var,
    )


# ---------------------------------------------------------------------------
# Parser de definición completa
# ---------------------------------------------------------------------------

_DEFINITION_RE = re.compile(
    r"^\s*(?P<name>[^(]+?)\s*\((?P<fields>[^)]+)\)\s*$"
)


def parse(definition: str, domain: str = "generic") -> EntityDef:
    """Parsea una definición de entidad y retorna un EntityDef.

    Formatos aceptados:
      "Cliente (id, nombre, dirección, teléfono)"
      "pedido"                         ← solo nombre
      "id, cliente_id, fecha, estado"  ← solo campos (nombre = "entidad")
    """
    definition = definition.strip()

    # Intentar formato "Nombre (campos...)"
    m = _DEFINITION_RE.match(definition)
    if m:
        raw_name = m.group("name").strip()
        raw_fields = m.group("fields")
    elif "," in definition and "(" not in definition:
        # Solo campos, sin nombre
        raw_name = "entidad"
        raw_fields = definition
    else:
        # Solo nombre
        raw_name = definition
        raw_fields = "id"

    snake_name = _to_snake(raw_name)
    class_name = _to_pascal(snake_name)
    table_name = _pluralize(snake_name)

    # Parsear campos
    field_names = [f.strip() for f in raw_fields.split(",") if f.strip()]

    # Asegurar que 'id' sea el primero
    if "id" not in [_to_snake(f) for f in field_names]:
        field_names = ["id"] + field_names

    fields: list[FieldDef] = []
    seen: set[str] = set()
    for fname in field_names:
        clean = _to_snake(fname)
        if clean in seen:
            continue
        seen.add(clean)
        fields.append(_infer_field(clean, domain))

    # Añadir timestamps si no están
    for ts in ("created_at", "updated_at"):
        if ts not in seen:
            fields.append(_infer_field(ts, domain))
            seen.add(ts)

    return EntityDef(
        raw_name=raw_name,
        snake_name=snake_name,
        class_name=class_name,
        table_name=table_name,
        fields=fields,
    )


def parse_many(text: str, domain: str = "generic") -> list[EntityDef]:
    """Parsea múltiples entidades separadas por salto de línea o punto y coma."""
    lines = re.split(r"[\n;]", text)
    results: list[EntityDef] = []
    for line in lines:
        line = line.strip()
        if line:
            results.append(parse(line, domain))
    return results


# ---------------------------------------------------------------------------
# Construcción del contexto Jinja2
# ---------------------------------------------------------------------------

def to_template_context(entity: EntityDef, package_name: str, created_at: str) -> dict:
    """Convierte un EntityDef en el contexto que usan los templates .j2."""

    # Imports Python
    imports: list[str] = []
    if entity.needs_optional:
        imports.append("Optional")
    if entity.needs_literal:
        imports.append("Literal")
    datetime_imports = sorted({
        f.extra_import for f in entity.fields
        if f.extra_import in ("datetime", "date")
    })
    decimal_import = "Decimal" if entity.needs_decimal else None

    # Tipos Literal para enums
    literal_types = [
        {
            "var_name": f.enum_var,
            "values_str": ", ".join(f'"{v}"' for v in f.enum_values),
        }
        for f in entity.enum_fields
    ]

    # Campos para el DTO
    dto_fields = []
    for f in entity.fields:
        dto_fields.append({
            "name": f.name,
            "python_type": f.python_type,
            "python_default": f.python_default,
            "comment": f.comment,
        })

    # Campos SQL — calcular ancho para alineación
    sql_fields = []
    col_width = max((len(f.name) for f in entity.fields), default=10) + 2
    for f in entity.fields:
        if f.is_pk:
            sql_def = f.sql_type
        elif f.is_fk:
            sql_def = f"INTEGER NOT NULL"
        else:
            sql_def = f.sql_type
        sql_fields.append({
            "name": f.name,
            "name_padded": f.name.ljust(col_width),
            "sql_def": sql_def,
            "comment": f.comment or "",
        })

    # FK constraints separadas (mejor legibilidad en SQL)
    fk_constraints = [
        {
            "field": f.name,
            "ref_table": f.fk_table,
            "constraint_name": f"fk_{entity.table_name}_{f.name}",
        }
        for f in entity.fk_fields
    ]

    # Índices automáticos
    indexes = []
    for f in entity.fk_fields:
        indexes.append({
            "name": f"idx_{entity.table_name}_{f.name}",
            "column": f.name,
        })
    for f in entity.enum_fields:
        indexes.append({
            "name": f"idx_{entity.table_name}_{f.name}",
            "column": f.name,
        })

    # Campos para repository (INSERT / UPDATE)
    insertable = [f.name for f in entity.insertable_fields]
    updatable  = [f.name for f in entity.updatable_fields]

    return {
        # Identidad
        "entity_name":  entity.snake_name,
        "class_name":   entity.class_name,
        "table_name":   entity.table_name,
        "package_name": package_name,
        "created_at":   created_at,

        # DTO
        "dto_fields":     dto_fields,
        "literal_types":  literal_types,
        "typing_imports": imports,
        "datetime_imports": datetime_imports,
        "decimal_import": decimal_import,

        # SQL
        "sql_fields":      sql_fields,
        "fk_constraints":  fk_constraints,
        "indexes":         indexes,

        # Repository
        "insertable_fields": insertable,
        "updatable_fields":  updatable,
    }
