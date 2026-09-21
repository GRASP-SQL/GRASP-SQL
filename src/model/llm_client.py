import json
import time
import re
from openai import OpenAI
from config.settings import SubgraphConfig

class LLMClient:
    def __init__(self, config: SubgraphConfig):
        self.client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
        self.cfg = config

    def chat_json(self, messages):
        for attempt in range(self.cfg.MAX_RETRIES):
            try:
                temp = self.cfg.TEMPERATURE + (attempt * 0.2)
                response = self.client.chat.completions.create(
                    model=self.cfg.MODEL_NAME,
                    messages=messages,
                    temperature=temp,
                    max_tokens=2048,
                    response_format={"type": "json_object"} 
                )
                content = response.choices[0].message.content
                return self._parse_json(content)
            except Exception as e:
                print(f"  [LLM Error] Attempt {attempt+1}: {e}")
                time.sleep(1 * (attempt + 1))
        return {}

    def _parse_json(self, text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {}
