# DataForge CLI

CLI para proyectos de datos con arquitectura en capas (Sources / DTOs / Transforms / Repositories / Services / CLI).

Reemplaza la nomenclatura MVC+DAO+DTO por una que calza mejor para ETL puro:

- **Sources**: fetchers (HTTP, APIs, scraping, archivos)
- **DTOs**: schemas Pydantic — contratos entre capas
- **Transforms**: limpieza, normalización, validación
- **Repositories**: acceso a Postgres vía psycopg3 + SQL crudo (patrón DAO)
- **Services**: orquestación — "fetch X, clean, validate, save"
- **CLI**: interfaz Typer (reemplaza a "View" de MVC)

## Instalación (modo desarrollo)

```bash
cd dataforge
pip install -e .
```

Disponible como `dataforge` o `dfg`.

## Comandos

```bash
dfg init <nombre>              # Crear proyecto ETL nuevo
dfg status                     # Info del proyecto actual
dfg add source <nombre>        # (stub) Añadir fuente de datos
dfg add entity <nombre>        # Añadir DTO + repositorio + migración SQL
dfg add pipeline <nombre>      # (stub) Añadir pipeline
dfg fetch <source>             # (stub) Ejecutar un fetcher
dfg run <pipeline>             # (stub) Ejecutar un pipeline
dfg inspect <tabla>            # (stub) Inspeccionar tabla en Postgres
dfg migrate                    # (stub) Aplicar migraciones SQL
```

Los stubs existen para que la superficie del CLI esté definida desde v0.1. Se implementan en orden de uso real.

## Principios

- **Simple > abstracto**. Repositorios con SQL crudo, no ORM. Queries visibles, debuggeables.
- **Aditivo**. `dfg add <cosa>` no toca nada existente, solo crea archivos nuevos.
- **Sin magia**. La configuración vive en `dataforge.toml` del proyecto. Nada oculto en variables globales.
- **Postgres local primero**. `docker-compose up` te da una DB local lista. Producción se configura cuando exista producción.

## Estructura de un proyecto generado

```
<proyecto>/
├── pyproject.toml
├── dataforge.toml          # Manifest (nombre, package, fuentes, pipelines)
├── docker-compose.yml      # Postgres 16 local
├── Makefile                # Comandos comunes (db, test, lint)
├── .env.example
├── src/<proyecto>/
│   ├── sources/            # Fetchers
│   ├── dtos/               # Pydantic schemas
│   ├── transforms/         # Limpieza y validación
│   ├── repositories/       # Acceso a Postgres
│   ├── services/           # Orquestación
│   ├── pipelines/          # Jobs ETL ejecutables
│   └── db/connection.py    # Pool de conexiones psycopg3
├── migrations/             # *.sql versionados
├── notebooks/              # Exploración
└── tests/
```
