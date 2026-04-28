"""Salida visual centralizada. Un solo lugar para el estilo del CLI."""
from __future__ import annotations

import contextlib
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich import box


class UI:
    """Wrapper delgado sobre Rich con prefijos consistentes."""

    def __init__(self) -> None:
        self.console = Console()

    # --- mensajes lineales ---
    def header(self, text: str) -> None:
        self.console.print()
        self.console.print(f"  [bold cyan]▸[/] [bold]{text}[/]")
        self.console.print(f"  [dim]{'─' * (len(text) + 2)}[/]")

    def success(self, text: str) -> None:
        self.console.print(f"  [bold green]✓[/] {text}")

    def error(self, text: str) -> None:
        self.console.print(f"  [bold red]✗[/] [red]{text}[/]")

    def warning(self, text: str) -> None:
        self.console.print(f"  [bold yellow]⚠[/] {text}")

    def info(self, text: str) -> None:
        self.console.print(f"  [dim]→ {text}[/]")

    def key_value(self, key: str, value: str) -> None:
        self.console.print(f"  [bold]{key}:[/] {value}")

    def newline(self) -> None:
        self.console.print()

    # --- archivos generados ---
    def file_created(self, path: str) -> None:
        self.console.print(f"  [green]+[/] [dim]{path}[/]")

    def file_modified(self, path: str) -> None:
        self.console.print(f"  [yellow]~[/] [dim]{path}[/]")

    # --- bloques ---
    def code(self, content: str, language: str = "python", title: Optional[str] = None) -> None:
        syntax = Syntax(content.strip(), language, theme="monokai", line_numbers=True, padding=1)
        if title:
            self.console.print(Panel(syntax, title=f"[dim]{title}[/]", border_style="dim"))
        else:
            self.console.print(Panel(syntax, border_style="dim"))

    def table(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: Optional[str] = None,
    ) -> None:
        t = Table(
            title=title,
            box=box.ROUNDED,
            border_style="dim",
            header_style="bold cyan",
            show_lines=False,
            padding=(0, 1),
        )
        for h in headers:
            t.add_column(h)
        for row in rows:
            t.add_row(*row)
        self.console.print(t)

    @contextlib.contextmanager
    def spinner(self, message: str = "Procesando..."):
        with Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[dim]{task.description}[/]"),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description=message, total=None)
            yield
