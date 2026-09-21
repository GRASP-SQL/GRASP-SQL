from __future__ import annotations

from collections import defaultdict

from src.llm import LLMClient
from config.runtime import LinkingSettings
from src.utils.graph import run_steiner_tree


class SchemaLinker:
    def __init__(self, client: LLMClient):
        self.client = client

    def select_columns(self, graph, question: str, evidence: str = "") -> list[str]:
        tables = defaultdict(list)
        for node_id, data in graph.nodes(data=True):
            if data.get("type") == "column":
                tables[data["table"]].append(node_id)
        schema = "\n".join(
            f"TABLE {name}: " + ", ".join(sorted(columns))
            for name, columns in sorted(tables.items())
        )
        reply = self.client.chat_json([{
            "role": "system",
            "content": "Return JSON only: target_columns and condition_columns. Values must match schema columns."
        }, {
            "role": "user",
            "content": f"Schema:\n{schema}\nQuestion: {question}\nEvidence: {evidence or 'None'}"
        }])
        values: list[object] = []
        for key in ("target_columns", "condition_columns"):
            candidate = reply.get(key, [])
            if isinstance(candidate, list):
                values.extend(candidate)
        return list(dict.fromkeys(value for value in values if isinstance(value, str)))


class SubgraphExtractor:
    def __init__(self, settings: LinkingSettings | None = None):
        self.settings = settings or LinkingSettings()

    def extract(self, graph, columns: list[str]) -> dict:
        identifiers = {str(node).lower(): node for node, data in graph.nodes(data=True)
                       if data.get("type") == "column"}
        terminals = [identifiers[column.lower()] for column in columns if column.lower() in identifiers]
        # A malformed LLM response must not erase the schema context. Falling back
        # to all columns preserves correctness at the cost of a larger prompt.
        if not terminals:
            terminals = list(identifiers.values())
        for _, _, edge in graph.edges(data=True):
            edge["weight"] = {
                "structure": self.settings.structure_weight,
                "foreign_key": self.settings.foreign_key_weight,
                "semantic": self.settings.similarity_weight,
                "similarity": self.settings.similarity_weight,
            }.get(edge.get("type"), self.settings.similarity_weight)
        node_ids = run_steiner_tree(graph, terminals)
        selected = set(node_ids)
        result_columns = []
        tables = set()
        for node_id in node_ids:
            data = graph.nodes[node_id]
            if data.get("type") == "column":
                result_columns.append({"id": node_id, **data})
                tables.add(data["table"])
            elif data.get("type") == "table":
                tables.add(data["name"])
        foreign_keys = [{"source": source, "target": target} for source, target, edge in graph.edges(data=True)
                        if edge.get("type") == "foreign_key" and source in selected and target in selected]
        return {"tables": sorted(tables), "columns": sorted(result_columns, key=lambda item: item["id"]),
                "foreign_keys": foreign_keys}
