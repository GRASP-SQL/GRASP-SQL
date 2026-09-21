from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sqlglot
import networkx as nx

from config.settings import GraphConfig
from src.data import load_dataset
from src.executor import execute_read_only
from src.graph_builder import SchemaGraphBuilder
from src.repair import SQLRepairer
from src.linking import SubgraphExtractor
from src.linking import SchemaLinker


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DB = ROOT / "data/databases/db_example/db_example.sqlite"


class DummyClient:
    def chat_text(self, _messages):
        return "SELECT 1"


class InvalidLinkerClient:
    def chat_json(self, _messages):
        return {"target_columns": [], "condition_columns": {"column": "items.id"}}


class CoreTests(unittest.TestCase):
    def test_spider_records_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spider.json"
            path.write_text(json.dumps([{"question_id": None, "db_id": "example", "question": "count", "query": "SELECT 1"}]))
            record = load_dataset(path, require_sql=True)[0]
        self.assertEqual(record["question_id"], 0)
        self.assertEqual(record["SQL"], "SELECT 1")

    def test_graph_uses_paper_edge_cost_order(self):
        graph = SchemaGraphBuilder("db_example", str(EXAMPLE_DB), "", GraphConfig()).build()
        costs = {edge["type"]: edge["weight"] for _, _, edge in graph.edges(data=True) if edge["type"] != "semantic"}
        self.assertLess(costs["structure"], costs["foreign_key"])

    def test_executor_is_read_only(self):
        result = execute_read_only(EXAMPLE_DB, "SELECT COUNT(*) FROM account")
        self.assertTrue(result.ok)
        self.assertEqual(result.rows[0][0], 4500)
        self.assertFalse(execute_read_only(EXAMPLE_DB, "DROP TABLE account").ok)

    def test_schema_patch_replaces_hallucinated_column(self):
        repairer = SQLRepairer(DummyClient())
        ast = sqlglot.parse_one("SELECT bogus FROM account", read="sqlite")
        patched = repairer._patch_schema(
            ast,
            "no such column: bogus",
            {"tables": ["account"], "columns": [{"id": "account.account_id", "name": "account_id"}]},
        )
        self.assertIn("account_id", patched.sql())

    def test_empty_linker_selection_keeps_schema(self):
        graph = nx.Graph()
        graph.add_node("items", type="table", name="items")
        graph.add_node("items.id", type="column", table="items", name="id", col_type="INTEGER")
        graph.add_edge("items", "items.id", type="structure", weight=0.1)
        subgraph = SubgraphExtractor().extract(graph, ["not.a.real.column"])
        self.assertEqual(["items.id"], [column["id"] for column in subgraph["columns"]])

    def test_linker_ignores_non_list_response_fields(self):
        graph = nx.Graph()
        graph.add_node("items.id", type="column", table="items", name="id")
        self.assertEqual([], SchemaLinker(InvalidLinkerClient()).select_columns(graph, "test"))


if __name__ == "__main__":
    unittest.main()
