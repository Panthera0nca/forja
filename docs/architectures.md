# Arquitecturas

forja soporta tres arquitecturas de scaffold. La elección depende del tipo de sistema que estás construyendo.

---

## ETL pipeline

Para proyectos orientados a ingesta, transformación y análisis de datos.

```bash
dfg init mi_proyecto --arch etl
```

```
src/<proyecto>/
├── sources/        # Fetchers: HTTP, APIs, archivos, DBs externas
├── dtos/           # Pydantic schemas — contratos entre capas
├── transforms/     # Funciones puras: limpieza, normalización
├── repositories/   # SQL crudo con psycopg3
├── services/       # Orquestación
├── pipelines/      # Jobs ETL ejecutables con `dfg run`
├── exporters/      # Salida a SQL o Excel
└── db/             # Pool de conexiones
```

**Cuándo usarla:** pipelines de datos, ingesta batch, análisis, reportes.

**Principios:**
- Sources solo traen datos, nunca validan ni transforman
- DTOs son el contrato entre capas — Pydantic valida en las fronteras
- Repositorios escriben SQL directo, sin ORM
- Pipelines orquestan: source → transform → repository

---

## Hexagonal (ports & adapters)

Para sistemas con dominio rico, reglas de negocio complejas y múltiples adaptadores.

```bash
dfg init mi_proyecto --arch hexagonal
```

```
src/<proyecto>/
├── domain/
│   ├── entities/      # Entidades del dominio
│   └── ports/         # Interfaces (Protocols)
├── application/
│   └── use_cases/     # Casos de uso
└── infrastructure/
    ├── db/            # Postgres
    └── repositories/  # Implementaciones concretas
```

**Cuándo usarla:** sistemas transaccionales, APIs con lógica de negocio, sistemas que necesitan ser testeados en aislamiento.

**Principios:**
- El dominio no depende de infraestructura
- Los ports (Protocols) definen contratos, no implementaciones
- Los use cases orquestan dominio + ports
- Infrastructure implementa los ports

---

## ML Pipeline

ETL completo más capas de Machine Learning. Framework-agnostic.

```bash
dfg init mi_proyecto --arch ml
pip install -e ".[dev,ml]"
```

```
src/<proyecto>/
├── sources/        # Ingesta (igual que ETL)
├── transforms/     # Limpieza + feature engineering
├── features/       # Feature store ligero
├── models/         # Predictor Protocol
├── evaluation/     # Métricas + cross-validation
├── pipelines/
│   ├── training.py     # train/val/test split → CV → fit → guardar
│   └── inference.py    # cargar modelo → predecir → persistir
└── repositories/   # Persistencia opcional
```

**Cuándo usarla:** modelos predictivos, clasificación, regresión, NLP, series de tiempo.

**Anti-overfitting integrado:**
- `Predictor` es un Protocol — sklearn, XGBoost, PyTorch: todos sirven
- Feature engineering separado del modelo
- `cross_validate()` incluido por defecto antes del fit final
- Test set tocado una sola vez, al final

```bash
dfg run training    # entrena, evalúa y guarda el modelo
dfg run inference   # carga modelo y predice sobre datos nuevos
```
