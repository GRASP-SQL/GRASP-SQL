"""Execution-accuracy evaluation for GRASP-SQL JSONL outputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from config.runtime import PipelineConfig
from src.data import load_dataset, read_jsonl
from src.executor import execute_read_only


def equivalent(predicted, gold_sql: str, database_path) -> tuple[bool, str | None]:
    gold = execute_read_only(database_path, gold_sql)
    predicted_result = execute_read_only(database_path, predicted)
    if not gold.ok:
        return False, f"gold query failed: {gold.error}"
    if not predicted_result.ok:
        return False, predicted_result.error
    if "order by" in gold_sql.lower():
        return gold.rows == predicted_result.rows, None
    return Counter(gold.rows or []) == Counter(predicted_result.rows or []), None


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate execution accuracy on BIRD or Spider")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--database-root", required=True)
    parser.add_argument("--limit", type=int, help="Evaluate only the first N dataset samples")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset, require_sql=True)
    if args.limit is not None:
        dataset = dataset[:args.limit]
    samples = {str(sample["question_id"]): sample for sample in dataset}
    predictions = {str(item["question_id"]): item for item in read_jsonl(args.predictions)}
    config = PipelineConfig.from_paths(database_root=args.database_root)
    totals, correct, missing = defaultdict(int), defaultdict(int), 0
    for question_id, sample in samples.items():
        prediction = predictions.get(question_id)
        difficulty = sample.get("difficulty", "overall")
        totals["overall"] += 1
        if difficulty != "overall":
            totals[difficulty] += 1
        if not prediction:
            missing += 1
            continue
        matched, _ = equivalent(prediction.get("sql", ""), sample["SQL"], config.database_path(sample["db_id"]))
        if matched:
            correct["overall"] += 1
            if difficulty != "overall":
                correct[difficulty] += 1
    for name in sorted(totals):
        print(f"{name}: {correct[name]}/{totals[name]} = {correct[name] / totals[name]:.2%}")
    print(f"missing predictions: {missing}")


if __name__ == "__main__":
    main()
