"""Motor de limpieza recursivo para proyectos DataForge.

Modelo de Calidad Recursivo (RQM):

    Q(nodo) = max(0, 1 - penalty(nodo))                    si hijos = ∅
    Q(nodo) = max(0, (1 - penalty(nodo)) × mean(Q(hijᵢ)))  si hijos ≠ ∅

    penalty(nodo) = min(1, Σ SEVERITY_WEIGHTS[issue.severity])

La recursión corre sobre un árbol:
  proyecto → capas (migrations, dtos, repos) → archivos
  schema   → tablas → columnas

El motor funciona dentro y fuera de un proyecto dfg, incluyendo
sobre el propio dfg (gestión holística).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Tipos de issues y severidades
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    # Proyecto — migraciones
    DUPLICATE_MIGRATION  = "duplicate_migration"
    MISSING_MIGRATION    = "missing_migration"
    INVALID_SQL          = "invalid_sql"
    MIGRATION_GAP        = "migration_gap"

    # Proyecto — capas
    ORPHAN_DTO           = "orphan_dto"
    ORPHAN_REPO          = "orphan_repo"
    MISSING_REPO         = "missing_repo"
    TEMPLATE_STUB        = "template_stub"

    # Datos — tabla
    DUPLICATE_ROWS       = "duplicate_rows"
    ORPHAN_FK            = "orphan_fk"
    NULL_REQUIRED        = "null_required"
    CHECK_VIOLATION      = "check_violation"

    # Datos — columna
    LOW_COMPLETENESS     = "low_completeness"
    LOW_UNIQUENESS       = "low_uniqueness"
    CONSTANT_COLUMN      = "constant_column"


SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 0.50,
    Severity.HIGH:     0.25,
    Severity.MEDIUM:   0.10,
    Severity.LOW:      0.03,
}

ISSUE_SEVERITIES: dict[IssueType, Severity] = {
    IssueType.DUPLICATE_MIGRATION:  Severity.HIGH,
    IssueType.MISSING_MIGRATION:    Severity.HIGH,
    IssueType.INVALID_SQL:          Severity.CRITICAL,
    IssueType.MIGRATION_GAP:        Severity.MEDIUM,
    IssueType.ORPHAN_DTO:           Severity.MEDIUM,
    IssueType.ORPHAN_REPO:          Severity.MEDIUM,
    IssueType.MISSING_REPO:         Severity.LOW,
    IssueType.TEMPLATE_STUB:        Severity.LOW,
    IssueType.DUPLICATE_ROWS:       Severity.HIGH,
    IssueType.ORPHAN_FK:            Severity.CRITICAL,
    IssueType.NULL_REQUIRED:        Severity.HIGH,
    IssueType.CHECK_VIOLATION:      Severity.HIGH,
    IssueType.LOW_COMPLETENESS:     Severity.MEDIUM,
    IssueType.LOW_UNIQUENESS:       Severity.MEDIUM,
    IssueType.CONSTANT_COLUMN:      Severity.LOW,
}


@dataclass
class Issue:
    type: IssueType
    message: str
    location: str                    # archivo, tabla o columna afectada
    fixable: bool = False
    fix_hint: str = ""
    detail: str = ""

    @property
    def severity(self) -> Severity:
        return ISSUE_SEVERITIES[self.type]

    @property
    def severity_icon(self) -> str:
        return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}[self.severity]


# ---------------------------------------------------------------------------
# Nodo del árbol de calidad (recursivo)
# ---------------------------------------------------------------------------

@dataclass
class CleaningNode:
    name: str
    level: str                       # "project"|"layer"|"file"|"schema"|"table"|"column"
    path: str = ""
    issues: list[Issue] = field(default_factory=list)
    children: list[CleaningNode] = field(default_factory=list)

    # ── Ecuación recursiva ──────────────────────────────────────────────────

    def quality_score(self) -> float:
        """Q(nodo) — puntuación de calidad en [0, 1]."""
        penalty = min(1.0, sum(SEVERITY_WEIGHTS[i.severity] for i in self.issues))

        if not self.children:
            # Caso base: nodo hoja
            return max(0.0, 1.0 - penalty)

        # Caso recursivo: promedio ponderado de hijos
        child_scores = [c.quality_score() for c in self.children]
        child_mean = sum(child_scores) / len(child_scores)
        return max(0.0, (1.0 - penalty) * child_mean)

    def all_issues(self) -> list[Issue]:
        """Recopila todos los issues del árbol (DFS)."""
        result = list(self.issues)
        for child in self.children:
            result.extend(child.all_issues())
        return result

    def fixable_issues(self) -> list[Issue]:
        return [i for i in self.all_issues() if i.fixable]

    def score_label(self) -> str:
        s = self.quality_score()
        if s >= 0.90: return "excelente"
        if s >= 0.75: return "bueno"
        if s >= 0.50: return "regular"
        if s >= 0.25: return "deficiente"
        return "crítico"


# ---------------------------------------------------------------------------
# ProjectCleaner — escanea estructura de archivos
# ---------------------------------------------------------------------------

_TABLE_FROM_CREATE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"']?(\w+)[\"']?",
    re.IGNORECASE,
)

_DOLLAR_QUOTE = re.compile(r"\$([A-Za-z_0-9]*)\$.*?\$\1\$", re.DOTALL)
_LINE_COMMENT  = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_SINGLE_QUOTE  = re.compile(r"'(?:[^']|'')*'", re.DOTALL)


def _strip_sql_literals(sql: str) -> str:
    """Remove comments, string literals, and dollar-quoted blocks before syntax checks."""
    sql = _DOLLAR_QUOTE.sub("", sql)
    sql = _BLOCK_COMMENT.sub("", sql)
    sql = _LINE_COMMENT.sub("", sql)
    sql = _SINGLE_QUOTE.sub("''", sql)
    return sql


_STUB_PATTERNS = [
    re.compile(r"name:\s+str\s*$", re.MULTILINE),
    re.compile(r"name\s+TEXT\s+NOT\s+NULL", re.IGNORECASE),
    re.compile(r"#\s+Añade aquí tus campos", re.IGNORECASE),
]


class ProjectCleaner:
    """Analiza la estructura de archivos de un proyecto DataForge."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def scan(self) -> CleaningNode:
        project_node = CleaningNode(
            name=self.root.name,
            level="project",
            path=str(self.root),
        )

        migrations_node = self._scan_migrations()
        dtos_node       = self._scan_dtos()
        repos_node      = self._scan_repos()
        cross_node      = self._scan_cross_layer(migrations_node, dtos_node, repos_node)

        project_node.children = [migrations_node, dtos_node, repos_node, cross_node]
        return project_node

    # ── Migraciones ─────────────────────────────────────────────────────────

    def _scan_migrations(self) -> CleaningNode:
        mig_dir = self.root / "migrations"
        node = CleaningNode(name="migrations", level="layer", path=str(mig_dir))

        if not mig_dir.exists():
            node.issues.append(Issue(
                IssueType.MISSING_MIGRATION, "Carpeta migrations/ no existe",
                location="migrations/", fixable=True, fix_hint="mkdir migrations",
            ))
            return node

        sql_files = sorted(mig_dir.glob("*.sql"))
        tables_seen: dict[str, list[str]] = {}   # table_name → [file, ...]
        last_num = -1

        for sql_file in sql_files:
            file_node = CleaningNode(
                name=sql_file.name, level="file", path=str(sql_file)
            )
            try:
                content = sql_file.read_text()
            except Exception as e:
                file_node.issues.append(Issue(
                    IssueType.INVALID_SQL, f"No se pudo leer: {e}",
                    location=sql_file.name,
                ))
                node.children.append(file_node)
                continue

            # Detectar gaps en numeración
            match = re.match(r"^(\d+)_", sql_file.name)
            if match:
                num = int(match.group(1))
                if last_num >= 0 and num != last_num + 1:
                    file_node.issues.append(Issue(
                        IssueType.MIGRATION_GAP,
                        f"Gap en numeración: esperado {last_num+1:03d}, encontrado {num:03d}",
                        location=sql_file.name,
                    ))
                last_num = num

            # Detectar tablas creadas
            tables = _TABLE_FROM_CREATE.findall(content)
            for table in tables:
                table = table.lower()
                if table == "_migrations":
                    continue
                tables_seen.setdefault(table, []).append(sql_file.name)

            # Detectar SQL inválido básico (paréntesis desbalanceados)
            # Strip comments/literals first to avoid false positives from
            # numbered list items like "1)" in comment text or PL/pgSQL bodies.
            stripped = _strip_sql_literals(content)
            if stripped.count("(") != stripped.count(")"):
                file_node.issues.append(Issue(
                    IssueType.INVALID_SQL,
                    "Paréntesis desbalanceados en SQL",
                    location=sql_file.name,
                ))

            node.children.append(file_node)

        # Reportar duplicados
        for table, files in tables_seen.items():
            if len(files) > 1:
                for fname in files[1:]:   # el primero es el original
                    target = next(
                        (c for c in node.children if c.name == fname), None
                    )
                    issue = Issue(
                        IssueType.DUPLICATE_MIGRATION,
                        f"Tabla '{table}' ya definida en {files[0]}",
                        location=fname,
                        fixable=True,
                        fix_hint=f"Eliminar {fname}",
                    )
                    if target:
                        target.issues.append(issue)
                    else:
                        node.issues.append(issue)

        return node

    # ── DTOs ────────────────────────────────────────────────────────────────

    def _scan_dtos(self) -> CleaningNode:
        dtos_dir = self.root / "src"
        node = CleaningNode(name="dtos", level="layer", path=str(dtos_dir))

        dto_files = [
            f for f in dtos_dir.rglob("*.py")
            if f.parent.name == "dtos" and f.name != "__init__.py"
        ]

        for dto_file in dto_files:
            file_node = CleaningNode(
                name=dto_file.name, level="file", path=str(dto_file)
            )
            try:
                content = dto_file.read_text()
                # Detectar stubs no editados
                for pattern in _STUB_PATTERNS:
                    if pattern.search(content):
                        file_node.issues.append(Issue(
                            IssueType.TEMPLATE_STUB,
                            "DTO contiene campos stub sin personalizar",
                            location=str(dto_file.relative_to(self.root)),
                            fixable=False,
                            fix_hint="Editar manualmente o regenerar con dfg add entity",
                        ))
                        break
            except Exception:
                pass
            node.children.append(file_node)

        return node

    # ── Repositorios ─────────────────────────────────────────────────────────

    def _scan_repos(self) -> CleaningNode:
        node = CleaningNode(name="repositories", level="layer")

        repo_files = [
            f for f in (self.root / "src").rglob("*.py")
            if f.parent.name == "repositories"
            and f.name not in ("__init__.py", "base.py")
        ]

        for repo_file in repo_files:
            node.children.append(CleaningNode(
                name=repo_file.name, level="file", path=str(repo_file)
            ))

        return node

    # ── Validación cruzada de capas ──────────────────────────────────────────

    def _scan_cross_layer(
        self,
        mig_node: CleaningNode,
        dto_node: CleaningNode,
        repo_node: CleaningNode,
    ) -> CleaningNode:
        node = CleaningNode(name="cross-layer", level="layer")

        dto_names = {
            c.name.replace(".py", "")
            for c in dto_node.children
        }
        repo_names = {
            re.sub(r"_repository\.py$", "", c.name)
            for c in repo_node.children
        }

        # DTOs sin repositorio
        for dto in dto_names:
            if dto not in repo_names:
                node.issues.append(Issue(
                    IssueType.MISSING_REPO,
                    f"DTO '{dto}.py' no tiene repositorio correspondiente",
                    location=f"src/.../dtos/{dto}.py",
                    fixable=True,
                    fix_hint=f"dfg add entity {dto}",
                ))

        # Repos sin DTO
        for repo in repo_names:
            if repo not in dto_names:
                node.issues.append(Issue(
                    IssueType.ORPHAN_REPO,
                    f"Repositorio '{repo}_repository.py' no tiene DTO",
                    location=f"src/.../repositories/{repo}_repository.py",
                ))

        return node

    # ── Fix automático ───────────────────────────────────────────────────────

    def fix(self, node: CleaningNode, dry_run: bool = False) -> list[str]:
        """Aplica fixes automáticos a los issues fixables. Retorna log de acciones."""
        actions: list[str] = []
        for issue in node.all_issues():
            if not issue.fixable:
                continue
            if issue.type == IssueType.DUPLICATE_MIGRATION:
                path = self.root / "migrations" / issue.location
                if path.exists():
                    action = f"Eliminar {issue.location}"
                    actions.append(action)
                    if not dry_run:
                        path.unlink()
        return actions


# ---------------------------------------------------------------------------
# DataCleaner — escanea calidad de datos en PostgreSQL
# ---------------------------------------------------------------------------

class DataCleaner:
    """Analiza calidad de datos en las tablas PostgreSQL del proyecto."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def scan(self, tables: Optional[list[str]] = None) -> CleaningNode:
        """Escanea el schema y retorna el árbol de calidad."""
        schema_node = CleaningNode(name="database", level="schema")

        try:
            import psycopg
            with psycopg.connect(self.database_url) as conn:
                available = self._get_tables(conn)
                target = [t for t in available if t not in ("_migrations",)]
                if tables:
                    target = [t for t in target if t in tables]

                for table in target:
                    table_node = self._scan_table(conn, table)
                    schema_node.children.append(table_node)

        except Exception as e:
            schema_node.issues.append(Issue(
                IssueType.INVALID_SQL,
                f"No se pudo conectar a la base de datos: {e}",
                location="database",
            ))

        return schema_node

    def _get_tables(self, conn) -> list[str]:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            return [row[0] for row in cur.fetchall()]

    def _scan_table(self, conn, table: str) -> CleaningNode:
        table_node = CleaningNode(name=table, level="table", path=table)

        with conn.cursor() as cur:
            # Total de filas
            cur.execute(f"SELECT COUNT(*) FROM {table};")  # noqa: S608
            total = cur.fetchone()[0]

            if total == 0:
                return table_node

            # Duplicados exactos
            cur.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT COUNT(*) FROM {table}
                    GROUP BY ctid::text HAVING COUNT(*) > 1
                ) sub;
            """)
            # Alternativa más robusta: duplicados por todos los campos excepto id
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, (table,))
            columns = [row[0] for row in cur.fetchall()]

            non_id_cols = [c for c in columns if c not in ("id", "created_at", "updated_at")]
            if non_id_cols:
                cols_csv = ", ".join(non_id_cols)
                cur.execute(f"""
                    SELECT COUNT(*) FROM (
                        SELECT {cols_csv}, COUNT(*) as cnt
                        FROM {table}
                        GROUP BY {cols_csv}
                        HAVING COUNT(*) > 1
                    ) dups;
                """)
                dup_count = cur.fetchone()[0]
                if dup_count > 0:
                    table_node.issues.append(Issue(
                        IssueType.DUPLICATE_ROWS,
                        f"{dup_count} grupo(s) de filas duplicadas detectados",
                        location=table,
                        fixable=True,
                        fix_hint=f"DELETE FROM {table} WHERE id NOT IN (SELECT MIN(id) FROM {table} GROUP BY {cols_csv})",
                        detail=f"Total filas: {total}",
                    ))

            # FK violations
            cur.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS ref_table,
                    ccu.column_name AS ref_col
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name = %s;
            """, (table,))
            fks = cur.fetchall()

            for col, ref_table, ref_col in fks:
                cur.execute(f"""
                    SELECT COUNT(*) FROM {table} t
                    WHERE t.{col} IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM {ref_table} r WHERE r.{ref_col} = t.{col}
                      );
                """)
                orphans = cur.fetchone()[0]
                if orphans > 0:
                    table_node.issues.append(Issue(
                        IssueType.ORPHAN_FK,
                        f"{orphans} registro(s) con FK '{col}' → '{ref_table}' sin referencia",
                        location=f"{table}.{col}",
                        fixable=False,
                    ))

            # Calidad por columna
            for col in columns:
                col_node = self._scan_column(conn, table, col, total)
                table_node.children.append(col_node)

        return table_node

    def _scan_column(self, conn, table: str, column: str, total: int) -> CleaningNode:
        col_node = CleaningNode(name=column, level="column", path=f"{table}.{column}")

        with conn.cursor() as cur:
            # Completitud: % de no nulos
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL;")
            null_count = cur.fetchone()[0]
            completeness = 1.0 - (null_count / total) if total > 0 else 1.0

            if completeness < 0.95 and null_count > 0:
                severity = Severity.HIGH if completeness < 0.70 else Severity.MEDIUM
                col_node.issues.append(Issue(
                    IssueType.LOW_COMPLETENESS,
                    f"{null_count}/{total} nulos ({(1-completeness)*100:.1f}% vacío)",
                    location=f"{table}.{column}",
                ))

            # Unicidad: detectar columnas constantes
            cur.execute(f"SELECT COUNT(DISTINCT {column}) FROM {table};")
            distinct = cur.fetchone()[0]

            if total > 10 and distinct == 1:
                col_node.issues.append(Issue(
                    IssueType.CONSTANT_COLUMN,
                    f"Columna constante: todos los valores son iguales",
                    location=f"{table}.{column}",
                ))
            elif total > 100 and distinct / total < 0.01:
                col_node.issues.append(Issue(
                    IssueType.LOW_UNIQUENESS,
                    f"Muy baja cardinalidad: {distinct} valores distintos en {total} filas",
                    location=f"{table}.{column}",
                ))

        return col_node
