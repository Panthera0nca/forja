# Dominios

forja detecta el dominio de tu proyecto automáticamente por nombre usando un clasificador ML. Podés confirmarlo, cambiarlo o forzarlo con `--domain`.

---

## Dominios integrados

### `health` — Salud / Epidemiología
Sistemas clínicos, epidemiológicos o de salud pública.

- **Arquitectura sugerida:** hexagonal
- **Entidades típicas:** paciente, diagnostico, medicamento, cita, resultado
- **Features activadas:** audit_log, soft_delete, gdpr

```bash
dfg init sistema_clinico --domain health
```

---

### `finance` — Finanzas / Portfolio
Transacciones, cuentas, portfolio de inversión y métricas de riesgo.

- **Arquitectura sugerida:** hexagonal
- **Entidades típicas:** cuenta, transaccion, factura, pago, balance, posicion
- **Features activadas:** audit_log, immutable_records, double_entry, time_series

```bash
dfg init gestion_cartera --domain finance
```

---

### `logistics` — Logística / Delivery
Gestión de rutas, pedidos, repartidores y tracking.

- **Arquitectura sugerida:** hexagonal
- **Entidades típicas:** cliente, repartidor, pedido, ruta, asignacion
- **Features activadas:** state_machine, audit_log

```bash
dfg init sistema_despacho --domain logistics
```

---

### `ecommerce` — E-Commerce
Catálogo, órdenes, pagos y gestión de inventario.

- **Arquitectura sugerida:** hexagonal
- **Entidades típicas:** producto, categoria, orden, cliente, pago, inventario
- **Features activadas:** state_machine, soft_delete, audit_log

```bash
dfg init tienda_online --domain ecommerce
```

---

### `education` — Educación
Gestión académica: cursos, estudiantes, calificaciones.

- **Arquitectura sugerida:** etl
- **Entidades típicas:** estudiante, curso, profesor, inscripcion, calificacion

```bash
dfg init plataforma_cursos --domain education
```

---

### `climate` — Clima / Medioambiente
Datos ambientales, estaciones meteorológicas, emisiones.

- **Arquitectura sugerida:** etl
- **Entidades típicas:** estacion, medicion, contaminante, region, reporte
- **Features activadas:** time_series

```bash
dfg init monitor_calidad_aire --domain climate
```

---

### `social_science` — Ciencias Sociales
Encuestas, demografía, análisis socioeconómico.

- **Arquitectura sugerida:** etl
- **Entidades típicas:** encuesta, respuesta, indicador, region, periodo
- **Features activadas:** time_series

```bash
dfg init analisis_electoral --domain social_science
```

---

### `bioinformatics` — Bioinformática / Omics
Pipelines genómicos, proteómicos, metabolómicos y metagenómicos.

- **Arquitectura sugerida:** etl
- **Entidades típicas:** muestra, run_secuenciacion, variante, gen, resultado_analisis
- **Features activadas:** time_series, audit_log

```bash
dfg init pipeline_rnaseq --domain bioinformatics
```

---

### `generic` — Genérico / ETL
Pipeline de datos sin dominio específico.

- **Arquitectura sugerida:** etl

```bash
dfg init mi_pipeline --domain generic
```

---

## Agregar dominios via plugins

Con el plugin system podés registrar dominios propios que el clasificador detectará automáticamente:

```python
# mi_plugin/plugin.py
def register(registry):
    registry.add_domain(
        key="pharma",
        display_name="Farmacéutica",
        description="Ensayos clínicos y trazabilidad regulatoria",
        architecture="hexagonal",
        keywords=["medicamento", "ensayo", "clinico", "dosis", "lote"],
        suggested_entities=["medicamento", "ensayo_clinico", "lote"],
    )
```

Ver [Plugins](plugins.md) para más detalles.
