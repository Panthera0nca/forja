"""Services: orquestación entre sources, transforms y repositories.

Un servicio típico: "trae X de la fuente, validá, guarda en Postgres, devolvé resumen".
Los servicios NO hacen I/O directo a Postgres — delegan a repositorios.
"""
