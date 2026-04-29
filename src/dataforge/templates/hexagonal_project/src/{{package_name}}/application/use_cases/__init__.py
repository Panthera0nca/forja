"""Casos de uso — orquestan entidades de dominio y ports.

Convención:
- Cada caso de uso es una clase con un único método público `execute(...)`.
- Reciben sus dependencias (repositorios, servicios) vía constructor (DI manual).
- No importan nada de infrastructure/ directamente.
"""
