"""`dfg plugins` — listar plugins de forja instalados."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from dataforge.core.plugins import get_registry
from dataforge.core.ui import UI

console = Console()


def plugins() -> None:
    ui = UI()
    registry = get_registry()

    ui.header("Plugins instalados")

    if not registry.sources:
        ui.warning("Sin plugins instalados.")
        ui.newline()
        ui.info("Para crear un plugin:")
        ui.info("  Declarar entry point en pyproject.toml:")
        ui.info('  [project.entry-points."forja.plugins"]')
        ui.info('  mi_plugin = "mi_paquete.plugin:register"')
        return

    # Dominios registrados por plugins
    plugin_domains = [d for d in registry.domains.values()]
    plugin_archs = [a for a in registry.architectures.values()]

    console.print(f"\n  [bold]{len(registry.sources)} plugin(s) cargados:[/bold]  "
                  f"{', '.join(registry.sources)}\n")

    if plugin_domains:
        t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        t.add_column("Dominio")
        t.add_column("Nombre")
        t.add_column("Arquitectura")
        t.add_column("Plugin")

        for d in plugin_domains:
            t.add_row(d.key, d.display_name, d.architecture, d.source or "—")

        console.print("  [bold]Dominios:[/bold]")
        console.print(t)

    if plugin_archs:
        console.print()
        t2 = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        t2.add_column("Arquitectura")
        t2.add_column("Descripción")
        t2.add_column("Plugin")

        for a in plugin_archs:
            t2.add_row(a.key, a.description, a.source or "—")

        console.print("  [bold]Arquitecturas:[/bold]")
        console.print(t2)

    console.print()
