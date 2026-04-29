# Referencia de comandos

## `dfg init`

Crea un proyecto nuevo con wizard de dominio y arquitectura.

```bash
dfg init <nombre> [opciones]
```

| Opción | Descripción |
|---|---|
| `--domain` | Forzar dominio (ej: `health`, `finance`) |
| `--arch` | Forzar arquitectura (`etl`, `hexagonal`, `ml`) |
| `--package` | Nombre del package Python (default: derivado del nombre) |
| `--no-wizard` | Saltar el wizard interactivo |
| `--force` | Sobrescribir si ya existe |

```bash
dfg init analisis_covid
dfg init detector_fraude --arch ml
dfg init pipeline_datos --domain generic --no-wizard
```

---

## `dfg classify`

Clasifica el dominio de un nombre sin crear archivos.

```bash
dfg classify <texto>
```

```bash
dfg classify sistema_pacientes    # → Salud / Epidemiología (89%)
dfg classify logistics_tracker    # → Logística / Delivery (94%)
```

---

## `dfg status`

Muestra información del proyecto actual (detecta `dataforge.toml` subiendo por el árbol).

```bash
dfg status
```

---

## `dfg doctor`

Diagnóstico de salud del proyecto.

```bash
dfg doctor [--fix]
```

Verifica: `.env`, Docker, tests, migraciones, sources/pipelines/exporters implementados, package importable.

---

## `dfg add`

### `dfg add entity`

Genera DTO Pydantic + repositorio SQL + migración versionada.

```bash
dfg add entity "Paciente (nombre, edad, diagnostico, admitido_at)"
dfg add entity "Transaccion (monto, moneda, estado, cuenta_id)" --yes
```

Inferencia automática de tipos:

| Patrón | Tipo SQL | Tipo Python |
|---|---|---|
| `_id` al final | `INTEGER` + FK | `Optional[int]` |
| `_at` al final | `TIMESTAMPTZ` | `Optional[datetime]` |
| `monto`, `precio`, `total` | `NUMERIC` | `Decimal` |
| `estado`, `tipo`, `categoria` | `TEXT` (ENUM) | `Literal[...]` |
| otros | `TEXT` | `str` |

### `dfg add source`

Genera un fetcher en `sources/<nombre>.py`.

```bash
dfg add source api_hl7
dfg add source csv_ventas --yes
```

### `dfg add pipeline`

Genera un pipeline en `pipelines/<nombre>.py` listo para `dfg run`.

```bash
dfg add pipeline ingestion_diaria
dfg add pipeline training --yes
```

### `dfg add exporter`

Genera un exporter en `exporters/<nombre>_<formato>.py`.

```bash
dfg add exporter ordenes --format sql
dfg add exporter pacientes --format excel
```

---

## `dfg fetch`

Corre un source en aislamiento para debugging.

```bash
dfg fetch <source> [--limit N] [--dry-run] [--list]
```

```bash
dfg fetch api_shopify
dfg fetch api_shopify --limit 3
dfg fetch --list          # ver sources disponibles
```

---

## `dfg run`

Ejecuta un pipeline del proyecto.

```bash
dfg run <pipeline> [--dry-run] [--list]
```

```bash
dfg run ingestion_diaria
dfg run training
dfg run --list            # ver pipelines disponibles
```

---

## `dfg export`

Corre un exporter y escribe el archivo de salida.

```bash
dfg export <exporter> [--dest ruta] [--limit N] [--no-db] [--list]
```

```bash
dfg export ordenes_excel
dfg export ordenes_sql --dest /tmp/backup.sql
dfg export ordenes_excel --no-db   # test sin conectar a DB
```

---

## `dfg inspect`

Schema + estadísticas descriptivas + muestra de filas desde Postgres.

```bash
dfg inspect <tabla> [--limit N] [--no-stats]
```

```bash
dfg inspect pacientes
dfg inspect transacciones --limit 20
dfg inspect grandes_tabla --no-stats
```

---

## `dfg migrate`

Aplica migraciones SQL versionadas (archivos `.sql` en `migrations/`).

```bash
dfg migrate [--dry-run] [--to archivo.sql]
```

```bash
dfg migrate
dfg migrate --dry-run
dfg migrate --to 003_add_index.sql
```

Cada migración se aplica exactamente una vez. El estado se guarda en la tabla `_dataforge_migrations`.

---

## `dfg upgrade`

Actualiza un proyecto generado con una versión anterior de forja.

```bash
dfg upgrade [--dry-run]
```

```bash
dfg upgrade --dry-run   # ver qué se agregaría
dfg upgrade             # aplicar cambios
```

---

## `dfg plugins`

Lista los plugins de forja instalados y qué registran.

```bash
dfg plugins
```

---

## `dfg version`

Muestra la versión instalada de forja.

```bash
dfg version
```
