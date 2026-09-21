"""Schema serialization and SQL response extraction."""

from __future__ import annotations


class SchemaFormatter:
    def format(self, subgraph: dict) -> str:
        tables = {table: [] for table in subgraph.get("tables", [])}
        for column in subgraph.get("columns", []):
            details = [str(column.get("col_type") or "UNKNOWN")]
            if column.get("column_description"):
                details.append(f"description: {column['column_description']}")
            examples = column.get("examples") or []
            if examples:
                details.append("examples: " + ", ".join(str(value) for value in examples[:2]))
            tables.setdefault(column["table"], []).append(
                f"{column['id']} ({'; '.join(details)})"
            )
        lines = [
            f"TABLE {table}: " + ", ".join(sorted(columns))
            for table, columns in sorted(tables.items())
        ]
        if subgraph.get("foreign_keys"):
            lines.append("FOREIGN KEYS: " + "; ".join(
                sorted(f"{edge['source']} = {edge['target']}" for edge in subgraph["foreign_keys"])
            ))
        return "\n".join(lines)


def extract_sql(text: str) -> str:
    fence = chr(96) * 3
    value = text.strip()
    if fence in value:
        chunks = value.split(fence)
        if len(chunks) >= 3:
            value = chunks[1]
            if value.lower().startswith("sql"):
                value = value[3:]
    return value.strip().rstrip(";")
