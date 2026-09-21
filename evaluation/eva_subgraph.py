import json
import os
import argparse
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.utils.col_match import SQLUtils, MetricsCalculator

def load_predictions(file_path):
    print(f"Loading predictions from {file_path}...")
    preds = {}
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                qid = item.get("question_id") or item.get("id")
                
                col_list = []
                # Handle different formats
                if "columns" in item:
                    col_list = [c.get("id") if isinstance(c, dict) else c for c in item["columns"]]
                elif "target_set" in item:
                    col_list = item.get("target_set", []) + item.get("condition_set", [])
                
                col_cleaned = {SQLUtils.normalize_col(c) for c in col_list if c}
                preds[str(qid)] = col_cleaned
            except Exception as e:
                print(f"Warning: Failed to parse line: {e}")
    return preds

def load_gold(file_path):
    print(f"Loading gold data from {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Evaluate Subgraph Retrieval Quality")
    parser.add_argument("--pred_file", type=str, required=True, help="Path to prediction .jsonl")
    parser.add_argument("--gold_file", type=str, required=True, help="Path to gold .json")
    args = parser.parse_args()

    preds = load_predictions(args.pred_file)
    if not preds:
        return

    gold_data = load_gold(args.gold_file)
    if not gold_data:
        return

    metrics_acc = {"p": 0.0, "r": 0.0, "f1": 0.0}
    valid_count = 0

    for item in gold_data:
        qid = str(item.get("question_id"))
        
        if qid not in preds:
            continue
            
        pred_cols = preds[qid]
        gt_cols, gt_tables = SQLUtils.extract_gt_info(item.get("SQL") or item.get("sql"))

        p, r, f1, is_valid = MetricsCalculator.compute(pred_cols, gt_cols, gt_tables)

        if is_valid:
            metrics_acc["p"] += p
            metrics_acc["r"] += r
            metrics_acc["f1"] += f1
            valid_count += 1

    if valid_count == 0:
        print("No valid samples evaluated.")
        return

    avg_p = metrics_acc["p"] / valid_count
    avg_r = metrics_acc["r"] / valid_count
    avg_f1 = metrics_acc["f1"] / valid_count

    print("\n" + "=" * 50)
    print(f"SUBGRAPH EVALUATION")
    print(f"Valid Samples: {valid_count} / {len(gold_data)}")
    print("=" * 50)
    print(f"Recall:    {avg_r:.4f}")
    print(f"Precision: {avg_p:.4f}")
    print(f"F1-score:  {avg_f1:.4f}")
    print("=" * 50)

if __name__ == "__main__":
    main()

# python evaluation/eva_subgraph.py --pred_file schema_graphs/sub/example.jsonl --gold_file data/example.json
