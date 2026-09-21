"""Command-line entry point for GRASP-SQL inference."""

from __future__ import annotations

import argparse

from config.runtime import LLMConfig, PipelineConfig
from src.data import append_jsonl, load_dataset, processed_ids
from src.llm import LLMClient
from src.pipeline import GRASPPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GRASP-SQL LLM pipeline")
    parser.add_argument("--dataset", required=True, help="BIRD-style JSON dataset")
    parser.add_argument("--output", required=True, help="JSONL predictions path")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--database-root", help="Directory containing <db_id>/<db_id>.sqlite")
    parser.add_argument("--graph-root", default="schema_graphs/full")
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    samples = load_dataset(args.dataset)
    if args.limit is not None:
        samples = samples[:args.limit]
    done = processed_ids(args.output) if args.resume else set()
    pipeline = GRASPPipeline(
        LLMClient(LLMConfig.from_environment()),
        PipelineConfig.from_paths(
            args.data_root, args.graph_root, args.database_root, args.max_repairs
        ),
    )
    for sample in samples:
        if str(sample["question_id"]) in done:
            continue
        append_jsonl(args.output, pipeline.run_one(sample))


if __name__ == "__main__":
    main()
