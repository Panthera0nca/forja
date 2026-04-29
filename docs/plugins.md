# Plugins

El plugin system de forja permite extender el CLI con nuevos dominios y arquitecturas sin modificar forja directamente.

---

## Cómo funciona

forja descubre plugins via **Python entry points**. Al arrancar, carga todos los plugins instalados y los integra en el wizard, el clasificador y los scaffolds.

```bash
pip install forja-pharma   # instala el plugin
dfg plugins               # verifica que está cargado
dfg init mi_ensayo        # "Farmacéutica" aparece en el wizard
```

---

## Crear un plugin

### 1. Estructura del paquete

```
forja-mi-plugin/
├── pyproject.toml
└── src/
    └── forja_mi_plugin/
        ├── __init__.py
        └── plugin.py
```

### 2. `pyproject.toml`

```toml
[project]
name = "forja-mi-plugin"
version = "0.1.0"
dependencies = ["forja>=0.7.0"]

[project.entry-points."forja.plugins"]
mi_plugin = "forja_mi_plugin.plugin:register"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/forja_mi_plugin"]
```

### 3. `plugin.py`

```python
def register(registry):
    # Registrar un dominio
    registry.add_domain(
        key="pharma",                          # identificador único
        display_name="Farmacéutica",           # nombre en el wizard
        description="Ensayos clínicos y trazabilidad regulatoria",
        architecture="hexagonal",              # arquitectura sugerida
        keywords=[                             # para el clasificador ML
            "medicamento", "ensayo", "clinico",
            "dosis", "lote", "farmaco", "placebo",
        ],
        suggested_entities=[                   # sugerencias en dfg init
            "medicamento", "ensayo_clinico", "lote", "resultado",
        ],
    )
```

### 4. Publicar

```bash
hatch build
hatch publish
# pip install forja-mi-plugin
```

---

## Registrar una arquitectura personalizada

Si tu plugin incluye templates propios, podés registrar una nueva arquitectura:

```python
from pathlib import Path

def register(registry):
    registry.add_architecture(
        key="dbt",
        description="dbt pipeline — models / seeds / snapshots",
        template_path=Path(__file__).parent / "templates" / "dbt_project",
    )
```

El directorio `template_path` debe seguir las mismas convenciones que los templates de forja:
- Archivos `.j2` → renderizados con Jinja2
- Carpetas/archivos `_dotfile_X` → se convierten en `.X`
- Variables disponibles: `project_name`, `package_name`, `category`, `domain`, `python_version`, `forja_version`

---

## Verificar plugins instalados

```bash
dfg plugins
```

```
▸ Plugins instalados
────────────────────

1 plugin(s) cargados:  pharma

Dominios:
Dominio    Nombre          Arquitectura    Plugin
pharma     Farmacéutica    hexagonal       forja-pharma
```

---

## Convenciones de nombres

Los plugins de forja siguen la convención `forja-<nombre>` en PyPI:

- `forja-pharma` — dominio farmacéutico
- `forja-dbt` — arquitectura dbt
- `forja-retail` — dominio retail
