from src.model.llm_client import LLMClient
from src.templates.templates import LINKER_SYSTEM, LINKER_USER

class SchemaLinker:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_schema_text(self, G):
        schema_dict = {}
        for node_id, data in G.nodes(data=True):
            if data['type'] == 'column':
                t = data['table']
                desc = data.get('column_description', '')
                if t not in schema_dict: schema_dict[t] = []
                schema_dict[t].append(f"- {node_id} (Info: {desc})")
        
        lines = []
        for t, cols in schema_dict.items():
            lines.append(f"Table: {t}")
            lines.extend(cols)
            lines.append("")
        return "\n".join(lines)

    def predict(self, schema_text, question, evidence):
        user_content = LINKER_USER.format(
            schema_text=schema_text,
            question=question,
            evidence=evidence
        )
        
        messages = [
            {"role": "system", "content": LINKER_SYSTEM},
            {"role": "user", "content": user_content}
        ]
        print("LLM Input:", messages)
        response_json = self.llm.chat_json(messages)
        conds = response_json.get("condition_columns", [])
        targets = response_json.get("target_columns", [])
        return list(set(conds + targets))
