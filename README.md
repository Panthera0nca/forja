# forja · `dfg`

> Scaffolding inteligente para proyectos de datos en Python.

```bash
pip install forja
dfg init mi_proyecto
```

**forja** detecta el dominio de tu proyecto por nombre, propone una arquitectura en capas y genera el scaffold completo — listo para correr con Docker y Postgres en segundos.

---

## Por qué forja

La mayoría de los proyectos de datos empiezan igual: una carpeta con scripts sueltos, un notebook que creció demasiado y queries incrustadas en funciones. forja propone una estructura desde el día uno que escala sin reescribir.

- **Sin ORM.** SQL crudo en repositorios. Tus queries son visibles y debuggeables.
- **Sin magia.** La configuración vive en `dataforge.toml`. Nada oculto.
- **Aditivo.** `dfg add` nunca toca archivos existentes, solo crea nuevos.
- **ML-ready.** Arquitectura `ml` incluida: features, modelos, evaluación y cross-validation por defecto.

---

## Instalación

```bash
pip install forja
```

Requiere Python ≥ 3.10 y Docker (para Postgres local).

---

## Inicio rápido

```bash
# 1. Crear proyecto — el wizard detecta el dominio automáticamente
dfg init sistema_pacientes

# 2. Entrar al proyecto
cd sistema_pacientes

# 3. Levantar Postgres local
docker compose up -d

# 4. Instalar dependencias del proyecto
pip install -e ".[dev]"

# 5. Copiar variables de entorno
cp .env.example .env

# 6. Aplicar migraciones iniciales
dfg migrate

# 7. Verificar
dfg status
```

---

## Wizard de dominio

Al ejecutar `dfg init`, el clasificador detecta automáticamente el dominio del proyecto a partir de su nombre y propone la arquitectura más adecuada. El ejemplo a continuación muestra cómo funciona con un proyecto de genómica — pero el wizard aplica igual para cualquiera de los 9 dominios disponibles:

```
dfg init analisis_genomico

  Dominio                       Confianza
  Bioinformática / Omics   94%  ██████████████████  ● alta

  Dominio detectado: Bioinformática. ¿Cambiar? [y/N]:
  Arquitectura: ETL pipeline — sources / transforms / repositories / pipelines (recomendada)
  ¿Cambiar arquitectura? [y/N]:
```

**Dominios disponibles:** `health`, `finance`, `logistics`, `ecommerce`, `education`, `climate`, `social_science`, `bioinformatics`, `generic`.

El clasificador funciona en español e inglés. Si la confianza es baja, el wizard muestra todas las opciones para que elijas manualmente.

---

## Arquitecturas

### ETL pipeline
Para proyectos orientados a ingesta, transformación y análisis de datos.

```
src/<proyecto>/
├── sources/        # Fetchers: HTTP, APIs, archivos, DBs externas
├── dtos/           # Pydantic schemas — contratos entre capas
├── transforms/     # Funciones puras: limpieza, normalización
├── repositories/   # SQL crudo con psycopg3
├── services/       # Orquestación
├── pipelines/      # Jobs ETL ejecutables con `dfg run`
└── db/             # Pool de conexiones
```

### Hexagonal (ports & adapters)
Para sistemas con dominio rico, reglas de negocio y múltiples adaptadores.

```
src/<proyecto>/
├── domain/
│   ├── entities/
│   └── ports/      # Interfaces (Protocols)
├── application/
│   └── use_cases/
└── infrastructure/
    ├── db/
    └── repositories/
```

### ML Pipeline
ETL completo más capas de Machine Learning. Framework-agnostic.

```
src/<proyecto>/
├── sources/        # Ingesta (igual que ETL)
├── transforms/     # Limpieza + feature engineering
├── features/       # Feature store ligero
├── models/         # Predictor Protocol — sklearn, XGBoost, PyTorch: todos sirven
├── evaluation/     # Métricas + cross-validation por defecto
├── pipelines/
│   ├── training.py     # train/val/test split → CV → fit → evaluar → guardar
│   └── inference.py    # cargar modelo → predecir → persistir
└── repositories/   # Persistencia opcional
```

```bash
dfg init detector_fraude --arch ml
cd detector_fraude
pip install -e ".[dev,ml]"
```

---

## Comandos

### Scaffolding

```bash
dfg init <nombre>                         # Crear proyecto con wizard
dfg init <nombre> --domain finance        # Forzar dominio
dfg init <nombre> --arch ml               # Forzar arquitectura
dfg classify <nombre>                     # Clasificar dominio sin crear archivos
```

### Dentro de un proyecto

```bash
dfg status                                # Info del proyecto actual

dfg add entity "Paciente (nombre, edad, diagnostico)"   # DTO + repo + migración SQL
dfg add source api_hl7                    # Nuevo fetcher
dfg add pipeline ingestion_diaria         # Nuevo pipeline

dfg migrate                               # Aplicar migraciones pendientes
dfg migrate --dry-run                     # Ver qué correría sin aplicar
dfg migrate --to 003_add_index.sql        # Aplicar hasta un archivo específico

dfg run ingestion_diaria                  # Ejecutar pipeline
dfg run training                          # Ejecutar pipeline de entrenamiento ML
dfg run --list                            # Ver pipelines disponibles
```

---

## Generación de entidades

`dfg add entity` infiere tipos SQL y Python desde la definición en lenguaje natural:

```bash
dfg add entity "Transaccion (monto, moneda, estado, cliente_id, procesado_at)"
```

Genera:
- `dtos/transaccion.py` — modelo Pydantic con tipos inferidos
- `repositories/transaccion_repository.py` — CRUD con SQL crudo
- `migrations/001_create_transacciones.sql` — migración versionada

Inferencia automática: `_id` → FK, `_at` → `TIMESTAMPTZ`, `estado` → ENUM detectado por contexto de dominio, `monto` → `NUMERIC`.

---

## Migraciones

forja gestiona migraciones con una tabla `_dataforge_migrations` en tu base de datos:

```bash
dfg migrate           # aplica todas las pendientes en orden
dfg migrate --dry-run # muestra el plan sin tocar la DB
```

Cada archivo `.sql` en `migrations/` se aplica exactamente una vez. Si una falla, hace rollback solo de esa migración — las anteriores quedan intactas.

---

## Estructura de un proyecto generado

```
mi_proyecto/
├── dataforge.toml      # Manifest del proyecto
├── pyproject.toml
├── docker-compose.yml  # Postgres 16 local
├── Makefile            # make db / make test / make train
├── .env.example
├── src/mi_proyecto/    # Package Python
├── migrations/         # *.sql versionados
├── notebooks/          # Exploración con Jupytext
└── tests/
```

---

## Principios de diseño

- **SQL crudo, siempre.** Los repositorios escriben SQL directo. Sin ORM, sin magia, sin N+1 ocultos.
- **DTOs en las fronteras.** Los datos se validan al entrar y al salir, no dentro de la lógica.
- **Cross-validation por defecto.** En arquitectura ML, el scaffold ya incluye el helper de CV — el proyecto nace con buenas prácticas.
- **`Predictor` es un Protocol.** Cualquier objeto con `.fit()` y `.predict()` es un modelo válido.
- **Migraciones como código.** Archivos SQL versionados, aplicados en orden, con tracking en la DB.

---

## Licencia

MIT
