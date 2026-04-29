# Inicio rápido

## Instalación

```bash
pip install forja
```

## Tu primer proyecto

```bash
dfg init sistema_ventas
cd sistema_ventas
```

El wizard detecta el dominio **E-Commerce** automáticamente y propone la arquitectura ETL. Podés aceptar o cambiar.

```
Dominio                  Confianza
E-Commerce    94%  ██████████████████  ● alta

Dominio detectado: E-Commerce. ¿Cambiar? [y/N]:
Arquitectura: ETL pipeline (recomendada). ¿Cambiar? [y/N]:
```

## Levantar la infraestructura

```bash
docker compose up -d          # Postgres 16 local
pip install -e ".[dev]"       # dependencias del proyecto
cp .env.example .env          # variables de entorno
dfg migrate                   # migración inicial
dfg status                    # verificar
```

## Agregar una entidad

```bash
dfg add entity "Orden (cliente_id, monto, estado, procesado_at)"
```

forja infiere los tipos automáticamente:

- `cliente_id` → `INTEGER` + FK a `clientes`
- `monto` → `NUMERIC`
- `estado` → `TEXT` (ENUM si el dominio lo sugiere)
- `procesado_at` → `TIMESTAMPTZ`

Genera tres archivos:

```
dtos/orden.py                        # modelo Pydantic
repositories/orden_repository.py     # CRUD con SQL crudo
migrations/001_create_ordenes.sql    # migración versionada
```

## Agregar una fuente de datos

```bash
dfg add source api_shopify
```

Editá `src/sistema_ventas/sources/api_shopify.py` e implementá `fetch()`:

```python
def fetch(self) -> Iterable[dict]:
    response = httpx.get("https://api.shopify.com/orders.json", ...)
    for order in response.json()["orders"]:
        yield order
```

Testeá en aislamiento:

```bash
dfg fetch api_shopify --limit 5
```

## Agregar un pipeline

```bash
dfg add pipeline ingestion_diaria
```

Editá `src/sistema_ventas/pipelines/ingestion_diaria.py`:

```python
def run():
    source = ApiShopifySource()
    repo = OrdenRepository()
    for raw in source.fetch():
        orden = transform(raw)
        repo.save(orden)
```

Ejecutá:

```bash
dfg run ingestion_diaria
```

## Exportar datos

```bash
dfg add exporter ordenes --format excel
dfg export ordenes_excel
# → exports/ordenes_excel.xlsx listo para abrir en Excel
```

## Verificar la salud del proyecto

```bash
dfg doctor
```

```
✓  .env presente          ok
✓  docker-compose.yml     ok
✓  tests/test_*.py        ok
✓  migraciones (2)        ok
⚠  sources (0/1)          aviso  1 con NotImplementedError pendiente
✓  pipelines (1/1)        ok
✓  package importable     ok

⚠ 1 aviso(s) · 6 ok
```
