"""Dataset and JSONL helpers for BIRD-style and raw Spider records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

REQUIRED_FIELDS = {"question_id", "db_id", "question"}


def load_dataset(path: str | Path, require_sql: bool = False) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError(f"{path} must contain a JSON list")
    identifiers: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} is not an object")
        record = dict(record)
        if record.get("question_id") is None:
            record["question_id"] = index
        record.setdefault("evidence", "")
        if "SQL" not in record and record.get("query"):
            record["SQL"] = record["query"]
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            raise ValueError(f"Record {index} is missing {sorted(missing)}")
        if require_sql and not (record.get("SQL") or record.get("sql") or record.get("query")):
            raise ValueError(f"Record {index} has no reference SQL")
        identifier = str(record["question_id"])
        if identifier in identifiers:
            raise ValueError(f"Duplicate question_id {identifier}")
        identifiers.add(identifier)
        normalized.append(record)
    return normalized


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSONL at {path}:{line_number}") from error
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL record at {path}:{line_number} is not an object")
                yield value


def processed_ids(path: str | Path) -> set[str]:
    output = Path(path)
    return set() if not output.exists() else {str(row["question_id"]) for row in read_jsonl(output)}


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
