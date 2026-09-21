"""Build serialized schema graphs for all databases referenced by a dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from networkx.readwrite import json_graph
from tqdm import tqdm

from config.settings import GraphConfig
from src.data import load_dataset
from src.graph_builder import SchemaGraphBuilder


def database_path(database_root: Path, db_id: str) -> Path:
    path = database_root / db_id / f"{db_id}.sqlite"
    if not path.exists():
        raise FileNotFoundError(f"Database '{db_id}' was not found at {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GRASP-SQL heterogeneous schema graphs")
    parser.add_argument("--dataset", required=True, help="BIRD or raw Spider JSON file")
    parser.add_argument("--database-root", required=True, help="Directory containing database folders")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    databases = sorted({sample["db_id"] for sample in load_dataset(args.dataset)})
    database_root, output_dir = Path(args.database_root), Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for db_id in tqdm(databases, desc="Building schema graphs"):
        db_path = database_path(database_root, db_id)
        graph = SchemaGraphBuilder(
            db_id, str(db_path), str(db_path.parent / "database_description"), GraphConfig()
        ).build()
        with (output_dir / f"{db_id}.json").open("w", encoding="utf-8") as handle:
            json.dump(json_graph.node_link_data(graph, edges="links"), handle, ensure_ascii=False)


if __name__ == "__main__":
    main()
