import sys
import os
import json
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SubgraphConfig
from src.model.llm_client import LLMClient
from src.utils.graph import load_networkx_graph
from src.schema_linker import SchemaLinker
from src.subgraph_builder import SubgraphExtractor

def get_processed_ids(output_file):
    if not os.path.exists(output_file):
        return set()
    with open(output_file, 'r', encoding='utf-8') as f:
        return {json.loads(line).get("question_id") for line in f}

def main():
    cfg = SubgraphConfig()
    llm = LLMClient(cfg)
    linker = SchemaLinker(llm)
    extractor = SubgraphExtractor()

    with open(SubgraphConfig.DATA_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    processed_ids = get_processed_ids(SubgraphConfig.OUTPUT_PATH)
    print(f"Dataset: {len(dataset)} items. Resuming from {len(processed_ids)}...")

    graph_cache = {} 

    with open(SubgraphConfig.OUTPUT_PATH, 'a', encoding='utf-8') as f_out:
        for item in tqdm(dataset):
            q_id = item.get("question_id", dataset.index(item)) 
            
            if q_id in processed_ids:
                continue

            db_id = item['db_id']
            
            if db_id not in graph_cache:
                g_path = cfg.get_db_graph_path(cfg.GRAPH_ROOT, db_id)
                if not os.path.exists(g_path):
                    # tqdm.write(f"Graph missing: {db_id}")
                    continue
                graph_cache[db_id] = load_networkx_graph(g_path, cfg)
            
            G, id_map = graph_cache[db_id]
            if not G:
                continue

            # Schema Linking (LLM)
            schema_text = linker.generate_schema_text(G)
            raw_columns = linker.predict(
                schema_text, 
                item['question'], 
                item.get('evidence', '')
            )

            # Subgraph Extraction (Steiner Tree)
            subgraph_data = extractor.process(G, id_map, raw_columns)

            result = {
                "question_id": q_id,
                "db_id": db_id,
                # "question": item['question'],
                **subgraph_data
            }
            f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
            f_out.flush()

if __name__ == "__main__":
    main()
