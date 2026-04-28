-- Migración inicial.
--   1) Tabla de control de migraciones que usa `dfg migrate`.
--   2) Función reusable `touch_updated_at()` que cada entidad engancha vía trigger
--      para actualizar automáticamente la columna updated_at al hacer UPDATE.

CREATE TABLE IF NOT EXISTS _dataforge_migrations (
    id         SERIAL PRIMARY KEY,
    filename   TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    checksum   TEXT
);

CREATE INDEX IF NOT EXISTS idx_dataforge_migrations_applied_at
    ON _dataforge_migrations (applied_at DESC);

-- Función genérica: se define una sola vez, la reusan todas las tablas de entidades.
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
