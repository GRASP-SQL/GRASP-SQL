"""Runtime configuration for the end-to-end GRASP-SQL pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-chat"
    max_retries: int = 3
    timeout_seconds: float = 90.0
    temperature: float = 0.0
    max_tokens: int = 2048

    @classmethod
    def from_environment(cls) -> "LLMConfig":
        load_dotenv(override=False)
        api_key = os.getenv("GRASP_SQL_API_KEY", "")
        if not api_key:
            raise ValueError("GRASP_SQL_API_KEY is not set before invoking an LLM stage")
        return cls(
            api_key=api_key,
            base_url=os.getenv("GRASP_SQL_BASE_URL", cls.base_url),
            model_name=os.getenv("GRASP_SQL_MODEL", cls.model_name),
        )


@dataclass(frozen=True)
class GraphSettings:
    jaccard_threshold: float = 0.6
    sample_limit: int = 2
    sample_pool_size: int = 10_000
    max_text_length: int = 256


@dataclass(frozen=True)
class LinkingSettings:
    """Edge costs follow the paper: structure < foreign key < semantic."""

    structure_weight: float = 0.1
    foreign_key_weight: float = 0.2
    similarity_weight: float = 1.0


@dataclass(frozen=True)
class PipelineConfig:
    data_root: Path
    graph_root: Path
    database_root: Path | None = None
    max_repairs: int = 2
    execution_timeout_steps: int = 100_000
    require_non_empty_result: bool = True

    @classmethod
    def from_paths(
        cls,
        data_root: str | Path = "data",
        graph_root: str | Path = "schema_graphs/full",
        database_root: str | Path | None = None,
        max_repairs: int = 2,
    ) -> "PipelineConfig":
        return cls(
            Path(data_root),
            Path(graph_root),
            Path(database_root) if database_root else None,
            max_repairs=max_repairs,
        )

    def database_path(self, db_id: str) -> Path:
        roots = [self.database_root] if self.database_root else []
        roots += [self.data_root / "databases", self.data_root]
        for root in roots:
            candidate = root / db_id / f"{db_id}.sqlite"
            if candidate.exists():
                return candidate
        searched = ", ".join(str(root / db_id / f"{db_id}.sqlite") for root in roots)
        raise FileNotFoundError(f"Database '{db_id}' was not found. Searched: {searched}")

    def graph_path(self, db_id: str) -> Path:
        return self.graph_root / f"{db_id}.json"
