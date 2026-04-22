"""DTOs: Pydantic schemas que viajan entre capas.

Convención:
- `RawX` → lo que llega de una fuente externa (sin validar aún).
- `X` → el DTO canónico, validado y normalizado.
- `XCreate` / `XUpdate` → variantes para operaciones de escritura.
"""
