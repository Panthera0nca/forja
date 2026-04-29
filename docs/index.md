# forja

**Scaffolding inteligente para proyectos de datos en Python.**

```bash
pip install forja
dfg init mi_proyecto
```

forja detecta el dominio de tu proyecto por nombre, propone una arquitectura en capas y genera el scaffold completo — listo para correr con Docker y Postgres en segundos.

---

## Por qué forja

La mayoría de los proyectos de datos empiezan igual: una carpeta con scripts sueltos, un notebook que creció demasiado y queries incrustadas en funciones. forja propone una estructura desde el día uno que escala sin reescribir.

| | |
|---|---|
| **Sin ORM** | SQL crudo en repositorios. Tus queries son visibles y debuggeables. |
| **Sin magia** | La configuración vive en `dataforge.toml`. Nada oculto. |
| **Aditivo** | `dfg add` nunca toca archivos existentes, solo crea nuevos. |
| **ML-ready** | Arquitectura `ml` con features, modelos y cross-validation por defecto. |
| **Extensible** | Plugin system: terceros registran dominios y arquitecturas propias. |

---

## Instalación

```bash
pip install forja
```

Requiere Python ≥ 3.10 y Docker (para Postgres local).

---

## Flujo típico

```bash
# 1. Crear proyecto — el wizard detecta el dominio automáticamente
dfg init sistema_pacientes

# 2. Agregar componentes
dfg add entity "Paciente (nombre, edad, diagnostico)"
dfg add source api_hl7
dfg add pipeline ingestion_diaria

# 3. Correr y verificar
dfg migrate
dfg fetch api_hl7          # debug del source
dfg run ingestion_diaria   # ejecutar pipeline
dfg inspect pacientes      # explorar tabla
dfg doctor                 # salud del proyecto
```

---

## Wizard de dominio

Al ejecutar `dfg init`, el clasificador detecta el dominio del proyecto por su nombre y propone la arquitectura más adecuada. El ejemplo usa un proyecto de genómica — el wizard aplica igual para los 9 dominios disponibles: `health`, `finance`, `logistics`, `ecommerce`, `education`, `climate`, `social_science`, `bioinformatics`, `generic`.

Si la confianza es baja, el wizard muestra todas las opciones para que elijas manualmente. También podés forzar el dominio con `--domain`.

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `dfg init` | Crear proyecto con wizard de dominio |
| `dfg classify` | Clasificar dominio sin crear archivos |
| `dfg status` | Info del proyecto actual |
| `dfg doctor` | Diagnóstico de salud |
| `dfg add entity` | Generar DTO + repositorio + migración SQL |
| `dfg add source` | Nuevo fetcher de datos |
| `dfg add pipeline` | Nuevo pipeline ETL/ML |
| `dfg add exporter` | Exportar a SQL o Excel |
| `dfg fetch` | Correr un source en aislamiento |
| `dfg run` | Ejecutar un pipeline |
| `dfg export` | Correr un exporter |
| `dfg inspect` | Schema + estadísticas de una tabla |
| `dfg migrate` | Aplicar migraciones SQL versionadas |
| `dfg upgrade` | Actualizar proyecto a la versión actual |
| `dfg plugins` | Listar plugins instalados |
