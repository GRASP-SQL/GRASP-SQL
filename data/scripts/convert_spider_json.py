import json

INPUT_FILE = "spider-dev.json"
OUTPUT_FILE = "spider-dev-new.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

new_data = []

for idx, item in enumerate(data):
    new_item = {
        "question_id": idx,
        "db_id": item["db_id"],
        "question": item["question"],
        "evidence": "",
        "SQL": item["query"]
    }
    new_data.append(new_item)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=4, ensure_ascii=False)
