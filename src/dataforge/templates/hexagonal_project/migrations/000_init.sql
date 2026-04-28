-- Migración inicial — {{ project_name }}
-- Creado el: {{ created_at }}

-- Tabla de control de migraciones aplicadas
CREATE TABLE IF NOT EXISTS _migrations (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL UNIQUE,
    applied_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
