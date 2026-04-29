"""`dfg classify <texto>` — clasificar dominio sin crear nada."""
from __future__ import annotations

import typer

from dataforge.core.ui import UI
from dataforge.core.workflows import ARCHITECTURE_DESCRIPTIONS, get_workflow


def classify(
    text: str = typer.Argument(..., help="Nombre de proyecto o descripción a clasificar"),
) -> None:
    """Clasifica el dominio de un proyecto sin crear ningún archivo."""
    ui = UI()

    ui.header(f"Clasificando: '{text}'")
    ui.info("Entrenando clasificador...")

    try:
        from dataforge.core.classifier import top_domains
        top = top_domains(text, n=len([]))  # all domains
        top_3 = top_domains(text, n=3)
    except Exception as e:
        ui.error(f"Error en clasificador: {e}")
        raise typer.Exit(1)

    from rich.console import Console
    from rich.table import Table

    console = Console()
    ui.newline()

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
        title="Resultados del clasificador",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Dominio")
    table.add_column("Categoría", style="dim")
    table.add_column("Confianza", justify="right")
    table.add_column("Arquitectura sugerida", style="dim")

    for i, (domain, score) in enumerate(top_3, 1):
        wf = get_workflow(domain)
        bar = "█" * int(score * 15) + "░" * (15 - int(score * 15))
        conf_str = f"[{'green' if i == 1 else 'yellow'}]{bar} {score * 100:.0f}%[/]"
        arch_desc = ARCHITECTURE_DESCRIPTIONS.get(wf.architecture, wf.architecture)
        table.add_row(
            str(i),
            f"[bold]{wf.display_name}[/bold]" if i == 1 else wf.display_name,
            domain,
            conf_str,
            arch_desc,
        )

    console.print(table)

    # Detalle del dominio ganador
    best_domain, best_score = top_3[0]
    wf = get_workflow(best_domain)
    ui.newline()
    ui.key_value("Dominio", f"{wf.display_name} ({best_domain})")
    ui.key_value("Descripción", wf.description)
    ui.key_value("Arquitectura", ARCHITECTURE_DESCRIPTIONS[wf.architecture])

    if wf.suggested_entities:
        ui.key_value("Entidades sugeridas", ", ".join(wf.suggested_entities))
    if wf.features:
        ui.key_value("Features recomendadas", ", ".join(wf.features))
    if wf.notes:
        ui.info(f"  Nota: {wf.notes}")

    ui.newline()
    ui.info(f"Para crear el proyecto:  dfg init <nombre> --domain {best_domain}")
    ui.newline()
