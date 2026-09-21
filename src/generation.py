"""LLM rationale and SQL generation stages."""

from __future__ import annotations

import re

from src.llm import LLMClient
from src.prompting import SchemaFormatter, extract_sql
from src.templates.templates import RATIONALE_L_SYSTEM, RATIONALE_USER, SQL_SYSTEM, SQL_USER


class SQLGenerator:
    def __init__(self, client: LLMClient):
        self.client = client
        self.formatter = SchemaFormatter()

    def rationale(self, subgraph: dict, question: str, evidence: str = "") -> str:
        content = self.client.chat_text([
            {"role": "system", "content": RATIONALE_L_SYSTEM},
            {"role": "user", "content": RATIONALE_USER.format(
                schema_text=self.formatter.format(subgraph), question=question, evidence=evidence or "None"
            )},
        ], temperature=0.2)
        match = re.search(r"<reasoning>(.*?)</reasoning>", content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else content.strip()

    def generate(self, subgraph: dict, question: str, reasoning: str, evidence: str = "") -> str:
        content = self.client.chat_text([
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": SQL_USER.format(
                schema_text=self.formatter.format(subgraph), reasoning=reasoning,
                question=question, evidence=evidence or "None"
            )},
        ])
        return extract_sql(content)
