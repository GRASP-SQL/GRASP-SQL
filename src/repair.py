"""AST-grounded iterative repair for SQLite queries.

The repairer first performs the deterministic operations specified in the paper.
LLM calls are reserved for an unparsable query or a single affected major clause.
"""

from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

import sqlglot
from sqlglot import exp

from src.executor import ExecutionResult
from src.llm import LLMClient
from src.prompting import SchemaFormatter, extract_sql


class SQLRepairer:
    def __init__(self, client: LLMClient):
        self.client = client
        self.formatter = SchemaFormatter()

    def repair(
        self,
        subgraph: dict,
        question: str,
        sql: str,
        result: ExecutionResult,
        database_path: str | Path,
        evidence: str = "",
    ) -> tuple[str, str]:
        """Return repaired SQL and the strategy that produced it."""
        try:
            ast = sqlglot.parse_one(sql, read="sqlite")
        except Exception:
            return self._regenerate_query(subgraph, question, sql, result.error, evidence), "regenerate"

        error_type = self._classify(result)
        if error_type == "schema":
            patched = self._patch_schema(ast, result.error or "", subgraph)
            if patched:
                return patched.sql(dialect="sqlite"), "schema_patch"
        elif error_type == "value":
            patched = self._patch_values(ast, database_path)
            if patched:
                return patched.sql(dialect="sqlite"), "value_patch"

        return self._regenerate_clause(
            subgraph, question, sql, result.error or "", evidence
        ), "clause_patch"

    @staticmethod
    def _classify(result: ExecutionResult) -> str:
        error = (result.error or "").lower()
        if "no such column" in error or "no such table" in error:
            return "schema"
        if result.ok and not result.rows:
            return "value"
        return "structure"

    @staticmethod
    def _best_match(value: str, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        best = max(candidates, key=lambda candidate: SequenceMatcher(None, value.lower(), candidate.lower()).ratio())
        return best

    def _patch_schema(self, ast: exp.Expression, error: str, subgraph: dict) -> exp.Expression | None:
        match = re.search(r"no such (column|table):\s*([^\s]+)", error, re.IGNORECASE)
        if not match:
            return None
        kind, missing = match.group(1).lower(), match.group(2).strip("`\"[]")
        columns = subgraph.get("columns", [])
        candidates = list(subgraph.get("tables", [])) if kind == "table" else [
            candidate for column in columns for candidate in (column["id"], column["name"])
        ]
        replacement = self._best_match(missing, candidates)
        if not replacement:
            return None
        changed = False
        for column in ast.find_all(exp.Column):
            rendered = ".".join(part for part in (column.table, column.name) if part)
            if rendered.lower() == missing.lower() or column.name.lower() == missing.lower():
                table, _, name = replacement.rpartition(".")
                column.set("this", exp.to_identifier(name or replacement))
                if table:
                    column.set("table", exp.to_identifier(table))
                changed = True
        for table in ast.find_all(exp.Table):
            if table.name.lower() == missing.lower():
                table.set("this", exp.to_identifier(replacement.split(".", 1)[0]))
                changed = True
        return ast if changed else None

    def _patch_values(self, ast: exp.Expression, database_path: str | Path) -> exp.Expression | None:
        connection = sqlite3.connect(f"file:{Path(database_path).resolve()}?mode=ro", uri=True)
        try:
            for predicate in ast.find_all(exp.EQ):
                column, literal = predicate.left, predicate.right
                if not isinstance(column, exp.Column) or not isinstance(literal, exp.Literal) or not literal.is_string:
                    continue
                table = column.table
                if not table:
                    continue
                query = f"SELECT DISTINCT {self._quote(column.name)} FROM {self._quote(table)} WHERE {self._quote(column.name)} IS NOT NULL LIMIT 1000"
                try:
                    values = [str(row[0]) for row in connection.execute(query) if isinstance(row[0], str)]
                except sqlite3.Error:
                    continue
                candidate = self._best_match(literal.this, values)
                if candidate and candidate.lower() != literal.this.lower() and SequenceMatcher(None, literal.this.lower(), candidate.lower()).ratio() >= 0.65:
                    predicate.set("expression", exp.Literal.string(candidate))
                    return ast
        finally:
            connection.close()
        return None

    @staticmethod
    def _quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _regenerate_query(self, subgraph, question, sql, feedback, evidence) -> str:
        prompt = self._context(subgraph, question, evidence)
        prompt += f"\n[Invalid SQL]\n{sql}\n[Parser feedback]\n{feedback}\nReturn corrected SQLite SQL only."
        return extract_sql(self.client.chat_text([
            {"role": "system", "content": "Regenerate one valid read-only SQLite query. Output SQL only."},
            {"role": "user", "content": prompt},
        ]))

    def _regenerate_clause(self, subgraph, question, sql, feedback, evidence) -> str:
        start, end, clause = self._clause_span(sql, feedback)
        prompt = self._context(subgraph, question, evidence)
        prompt += (
            f"\n[Full SQL]\n{sql}\n[Failing clause]\n{clause}\n[Execution feedback]\n{feedback}"
            "\nReturn only a replacement for the failing clause, beginning with its clause keyword."
        )
        replacement = extract_sql(self.client.chat_text([
            {"role": "system", "content": "Repair only the supplied SQL clause. Output that clause only."},
            {"role": "user", "content": prompt},
        ]))
        if replacement.lower().startswith("select"):
            return replacement
        return sql[:start] + replacement.rstrip(";") + sql[end:]

    @staticmethod
    def _context(subgraph, question, evidence) -> str:
        return f"[Database Schema]\n{SchemaFormatter().format(subgraph)}\n\n[Question]\n{question}\n\n[Evidence]\n{evidence or 'None'}"

    @staticmethod
    def _clause_span(sql: str, feedback: str) -> tuple[int, int, str]:
        keywords = ("SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT")
        matches = list(re.finditer(r"\b(?:SELECT|FROM|WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT)\b", sql, re.IGNORECASE))
        if not matches:
            return 0, len(sql), sql
        cursor_match = re.search(r"(?:near|at)\s+['\"]([^'\"]+)", feedback, re.IGNORECASE)
        cursor = sql.lower().find(cursor_match.group(1).lower()) if cursor_match else -1
        index = next((i for i, item in enumerate(matches) if item.start() <= cursor < (matches[i + 1].start() if i + 1 < len(matches) else len(sql))), 0)
        start = matches[index].start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(sql)
        return start, end, sql[start:end]
