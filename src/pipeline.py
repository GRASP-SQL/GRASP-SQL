"""End-to-end GRASP-SQL inference pipeline."""

from __future__ import annotations

import time

from config.runtime import PipelineConfig
from config.settings import GraphConfig
from src.executor import execute_read_only
from src.generation import SQLGenerator
from src.graph_builder import SchemaGraphBuilder
from src.linking import SchemaLinker, SubgraphExtractor
from src.llm import LLMClient
from src.repair import SQLRepairer
from src.utils.graph import load_networkx_graph


class GRASPPipeline:
    def __init__(self, client: LLMClient, config: PipelineConfig):
        self.config = config
        self.linker = SchemaLinker(client)
        self.extractor = SubgraphExtractor()
        self.generator = SQLGenerator(client)
        self.repairer = SQLRepairer(client)
        self.client = client
        self.graphs = {}

    def _graph(self, db_id: str):
        if db_id not in self.graphs:
            serialized = self.config.graph_path(db_id)
            if serialized.exists():
                self.graphs[db_id], _ = load_networkx_graph(serialized)
            else:
                database = self.config.database_path(db_id)
                description = database.parent / "database_description"
                self.graphs[db_id] = SchemaGraphBuilder(
                    db_id, str(database), str(description), GraphConfig()
                ).build()
        return self.graphs[db_id]

    def run_one(self, sample: dict) -> dict:
        started = time.perf_counter()
        usage_before = (
            self.client.usage.prompt_tokens,
            self.client.usage.completion_tokens,
            self.client.usage.calls,
        )
        db_id = sample["db_id"]
        graph = self._graph(db_id)
        columns = self.linker.select_columns(graph, sample["question"], sample.get("evidence", ""))
        subgraph = self.extractor.extract(graph, columns)
        reasoning = self.generator.rationale(subgraph, sample["question"], sample.get("evidence", ""))
        sql = self.generator.generate(subgraph, sample["question"], reasoning, sample.get("evidence", ""))
        result = execute_read_only(
            self.config.database_path(db_id), sql, self.config.execution_timeout_steps
        )
        repairs = 0
        strategies = []
        while (
            (not result.ok or (self.config.require_non_empty_result and not result.rows))
            and repairs < self.config.max_repairs
        ):
            sql, strategy = self.repairer.repair(
                subgraph,
                sample["question"],
                sql,
                result,
                self.config.database_path(db_id),
                sample.get("evidence", ""),
            )
            strategies.append(strategy)
            result = execute_read_only(
                self.config.database_path(db_id), sql, self.config.execution_timeout_steps
            )
            repairs += 1
        return {
            "question_id": sample["question_id"],
            "db_id": db_id,
            "sql": sql,
            "reasoning": reasoning,
            "subgraph": subgraph,
            "execution_ok": result.ok,
            "execution_error": result.error,
            "repair_attempts": repairs,
            "repair_strategies": strategies,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "llm_usage": {
                "prompt_tokens": self.client.usage.prompt_tokens - usage_before[0],
                "completion_tokens": self.client.usage.completion_tokens - usage_before[1],
                "calls": self.client.usage.calls - usage_before[2],
            },
        }
