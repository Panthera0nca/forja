"""`dfg init <nombre>` — crear un proyecto nuevo con wizard de dominio."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.config import CATEGORIES
from dataforge.core.templates import render_template
from dataforge.core.ui import UI
from dataforge.core.workflows import get_workflow, get_all_workflows, get_all_architectures

PACKAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TEMPLATE_FOR_ARCH = {"hexagonal": "hexagonal_project", "etl": "etl_project", "ml": "ml_project"}

# Umbrales de confianza
_HIGH   = 0.70   # dominio claro → sugerir directamente
_MEDIUM = 0.40   # dominio probable → mostrar opciones con sugerencia
                 # < 0.40 → preguntar sin sugerencia


def _to_package_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).lower().strip("_")
    if not slug:
        slug = "project"
    if slug[0].isdigit():
        slug = f"p_{slug}"
    return slug


def _classify(text: str) -> tuple[str, float, list[tuple[str, float]]]:
    try:
        from dataforge.core.classifier import classify, top_domains
        domain, conf = classify(text)
        top = top_domains(text, n=3)
        return domain, conf, top
    except Exception:
        return "generic", 0.0, [("generic", 1.0)]


def _show_classifier_table(top: list[tuple[str, float]], confidence: float) -> None:
    console = Console()
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Dominio")
    table.add_column("Confianza", justify="right")
    table.add_column("Señal", justify="left")

    for i, (d, s) in enumerate(top):
        wf = get_workflow(d)
        bar = "█" * int(s * 18) + "░" * (18 - int(s * 18))
        if i == 0:
            if confidence >= _HIGH:
                signal = "[green]● alta[/green]"
                name_str = f"[bold green]{wf.display_name}[/bold green]"
            elif confidence >= _MEDIUM:
                signal = "[yellow]◐ media[/yellow]"
                name_str = f"[bold yellow]{wf.display_name}[/bold yellow]"
            else:
                signal = "[red]○ baja[/red]"
                name_str = f"[bold red]{wf.display_name}[/bold red]"
        else:
            signal = ""
            name_str = f"[dim]{wf.display_name}[/dim]"

        table.add_row(name_str, f"{s * 100:.0f}%  {bar}", signal)

    console.print(table)


def _ask_domain(ui: UI, detected: str, confidence: float) -> str:
    """Pregunta por el dominio según nivel de confianza."""
    domain_options = list(get_all_workflows().keys())
    wf = get_workflow(detected)

    if confidence >= _HIGH:
        # Confianza alta: confirmar o cambiar
        change = typer.confirm(
            f"  Dominio detectado: [bold]{wf.display_name}[/bold]. ¿Cambiar?",
            default=False,
        )
        if not change:
            return detected

    elif confidence >= _MEDIUM:
        # Confianza media: mostrar opciones con sugerencia marcada
        ui.warning(f"  Confianza media ({confidence*100:.0f}%) — verifica el dominio:")
        for i, d in enumerate(domain_options, 1):
            w2 = get_workflow(d)
            marker = " ◀ sugerido" if d == detected else ""
            ui.info(f"  {i:2}. {w2.display_name} ({d}){marker}")
        raw = typer.prompt(
            f"  Número o nombre de dominio (Enter = '{detected}')",
            default=detected,
        ).strip()
        if raw == detected or raw == "":
            return detected
        if raw.isdigit() and 1 <= int(raw) <= len(domain_options):
            return domain_options[int(raw) - 1]
        if raw in get_all_workflows():
            return raw
        ui.warning(f"Opción inválida, usando '{detected}'")
        return detected

    else:
        # Confianza baja: preguntar sin sugerencia fuerte
        ui.warning(
            f"  No pude determinar el dominio con certeza ({confidence*100:.0f}%). "
            "Elige manualmente:"
        )
        for i, d in enumerate(domain_options, 1):
            w2 = get_workflow(d)
            ui.info(f"  {i:2}. {w2.display_name} ({d})")
        raw = typer.prompt("  Número o nombre de dominio").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(domain_options):
            return domain_options[int(raw) - 1]
        if raw in get_all_workflows():
            return raw
        ui.warning(f"Opción inválida, usando 'generic'")
        return "generic"

    # Llegamos aquí si confidence >= HIGH y el usuario quiso cambiar
    for i, d in enumerate(domain_options, 1):
        w2 = get_workflow(d)
        ui.info(f"  {i:2}. {w2.display_name} ({d})")
    raw = typer.prompt("  Número o nombre de dominio").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(domain_options):
        return domain_options[int(raw) - 1]
    if raw in WORKFLOWS:
        return raw
    ui.warning(f"Opción inválida, usando '{detected}'")
    return detected


def _ask_arch(ui: UI, domain: str, confidence: float) -> str:
    """Propone arquitectura usando la confianza del dominio como señal."""
    wf = get_workflow(domain)
    suggested = wf.architecture
    arch_descriptions = get_all_architectures()
    arch_choices = list(arch_descriptions.keys())

    if confidence >= _HIGH:
        ui.key_value(
            "Arquitectura",
            f"{arch_descriptions.get(suggested, suggested)}  [green](recomendada)[/green]",
        )
        change = typer.confirm("  ¿Cambiar arquitectura?", default=False)
        if not change:
            return suggested

    elif confidence >= _MEDIUM:
        ui.warning(
            f"  Confianza media — arquitecturas disponibles "
            f"(sugerida: [bold]{suggested}[/bold]):"
        )
        for i, a in enumerate(arch_choices, 1):
            marker = " ◀ sugerida" if a == suggested else ""
            ui.info(f"  {i}. {arch_descriptions[a]}{marker}")
        raw = typer.prompt(
            f"  Número o nombre (Enter = '{suggested}')",
            default=suggested,
        ).strip()
        if raw in ("", suggested):
            return suggested
        if raw.isdigit() and 1 <= int(raw) <= len(arch_choices):
            return arch_choices[int(raw) - 1]
        if raw in arch_choices:
            return raw
        ui.warning(f"Opción inválida, usando '{suggested}'")
        return suggested

    else:
        ui.warning("  Elige la arquitectura del proyecto:")
        for i, a in enumerate(arch_choices, 1):
            ui.info(f"  {i}. {arch_descriptions[a]}")
        raw = typer.prompt("  Número o nombre de arquitectura").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(arch_choices):
            return arch_choices[int(raw) - 1]
        if raw in arch_choices:
            return raw
        ui.warning(f"Opción inválida, usando '{suggested}'")
        return suggested

    # Llegamos aquí si confidence >= HIGH y el usuario quiso cambiar
    for i, a in enumerate(arch_choices, 1):
        ui.info(f"  {i}. {arch_descriptions[a]}")
    raw = typer.prompt("  Número o nombre de arquitectura").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(arch_choices):
        return arch_choices[int(raw) - 1]
    if raw in arch_choices:
        return raw
    ui.warning(f"Opción inválida, usando '{suggested}'")
    return suggested


def init(
    name: str = typer.Argument(..., help="Nombre del proyecto (también nombre de carpeta)"),
    package: str | None = typer.Option(
        None, "--package", "-p",
        help="Nombre del package Python (default: derivado del nombre)",
    ),
    domain: str | None = typer.Option(
        None, "--domain", "-d",
        help="Forzar dominio sin wizard (ej: health, finance, logistics...)",
    ),
    arch: str | None = typer.Option(
        None, "--arch", "-a",
        help="Arquitectura: etl | hexagonal | ml (o arquitecturas de plugins)",
    ),
    no_wizard: bool = typer.Option(False, "--no-wizard", help="Saltar wizard interactivo"),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir si existe"),
) -> None:
    ui = UI()
    dest = Path(name)

    if dest.exists() and not force:
        ui.error(f"El directorio '{name}' ya existe. Usa --force para sobrescribir.")
        raise typer.Exit(1)

    pkg = package or _to_package_name(name)
    if not PACKAGE_NAME_RE.match(pkg):
        ui.error(f"Package '{pkg}' inválido. Debe ser snake_case empezando por letra.")
        raise typer.Exit(1)

    all_workflows = get_all_workflows()
    all_archs = get_all_architectures()

    if domain and domain not in all_workflows:
        ui.error(f"Dominio '{domain}' inválido. Opciones: {', '.join(all_workflows)}")
        raise typer.Exit(1)

    if arch and arch not in all_archs:
        ui.error(f"Arquitectura '{arch}' inválida. Opciones: {', '.join(all_archs)}")
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------
    ui.header(f"Iniciando proyecto '{name}'")

    if domain:
        detected_domain = domain
        confidence = 1.0
        top: list[tuple[str, float]] = [(domain, 1.0)]
    else:
        ui.info("Analizando nombre del proyecto...")
        detected_domain, confidence, top = _classify(name)

    ui.newline()
    _show_classifier_table(top, confidence)
    ui.newline()

    # ------------------------------------------------------------------
    # Wizard interactivo
    # ------------------------------------------------------------------
    chosen_domain = detected_domain
    chosen_arch = arch or get_workflow(detected_domain).architecture

    if not no_wizard:
        if not domain:
            chosen_domain = _ask_domain(ui, detected_domain, confidence)
            ui.newline()
        if not arch:
            chosen_arch = _ask_arch(ui, chosen_domain, confidence)
            ui.newline()

    # ------------------------------------------------------------------
    # Confirmación final
    # ------------------------------------------------------------------
    final_wf = get_workflow(chosen_domain)
    ui.key_value("Proyecto",     name)
    ui.key_value("Package",      pkg)
    ui.key_value("Dominio",      f"{final_wf.display_name} ({chosen_domain})")
    ui.key_value("Arquitectura", chosen_arch)
    if final_wf.suggested_entities:
        ui.key_value("Entidades sugeridas", ", ".join(final_wf.suggested_entities))
    ui.newline()

    # ------------------------------------------------------------------
    # Paso opcional: definir entidades ahora
    # ------------------------------------------------------------------
    entity_definitions: list[str] = []
    if not no_wizard:
        ui.newline()
        define_now = typer.confirm(
            "  ¿Definir entidades ahora?  "
            "(formato: Cliente (nombre, dirección, teléfono))",
            default=False,
        )
        if define_now:
            ui.info("  Ingresa una entidad por línea. Enter vacío para terminar.")
            ui.info("  Ejemplo:  Pedido (id, cliente_id, fecha, estado)")
            while True:
                raw = typer.prompt("  Entidad", default="").strip()
                if not raw:
                    break
                entity_definitions.append(raw)

    if not no_wizard:
        ui.newline()
        ok = typer.confirm("  ¿Crear proyecto con esta configuración?", default=True)
        if not ok:
            ui.info("Operación cancelada.")
            raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Renderizar template
    # ------------------------------------------------------------------
    template_name = TEMPLATE_FOR_ARCH[chosen_arch]
    now = datetime.now().strftime("%Y-%m-%d")
    from dataforge import __version__ as _forja_version
    context = {
        "project_name":    name,
        "package_name":    pkg,
        "category":        chosen_domain,
        "domain":          chosen_domain,
        "created_at":      now,
        "python_version":  "3.12",
        "postgres_image":  "postgres:16-alpine",
        "forja_version":   _forja_version,
    }

    ui.newline()
    ui.header(f"Generando scaffold '{name}' [{chosen_arch}]")
    created = render_template(template_name, dest, context)
    for path in created:
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        ui.file_created(str(rel))

    # ------------------------------------------------------------------
    # Generar entidades definidas en el wizard
    # ------------------------------------------------------------------
    if entity_definitions:
        from dataforge.core.entity_parser import parse, to_template_context
        from dataforge.core.templates import render_file
        from rich.console import Console
        from rich.table import Table

        ui.newline()
        ui.header("Generando entidades")

        migrations_dir = dest / "migrations"
        next_num = len(list(migrations_dir.glob("*.sql")))

        for raw_def in entity_definitions:
            try:
                entity = parse(raw_def, domain=chosen_domain)
                ectx = to_template_context(entity, package_name=pkg, created_at=now)

                dto_path  = dest / "src" / pkg / "dtos" / f"{entity.snake_name}.py"
                repo_path = dest / "src" / pkg / "repositories" / f"{entity.snake_name}_repository.py"
                mig_path  = migrations_dir / f"{next_num:03d}_create_{entity.table_name}.sql"

                render_file("components/entity/dto.py.j2",        dto_path,  ectx)
                render_file("components/entity/repository.py.j2", repo_path, ectx)
                render_file("components/entity/migration.sql.j2", mig_path,  ectx)

                ui.file_created(f"→ {entity.class_name}: DTO + repo + migración")
                next_num += 1

            except Exception as e:
                ui.warning(f"  No se pudo generar '{raw_def}': {e}")

    ui.newline()
    ui.success(f"Proyecto '{name}' creado — {len(created)} archivos")
    ui.info(f"→ cd {name}")
    ui.info("→ docker compose up -d")
    ui.info("→ pip install -e .")
    ui.info("→ dfg status")

    if not entity_definitions and final_wf.suggested_entities:
        ui.newline()
        ui.info("Entidades sugeridas para este dominio:")
        for e in final_wf.suggested_entities:
            ui.info(f"  dfg add entity \"{e.capitalize()} (id, ...)\"")
    ui.newline()
