import sys
import os
import json
import argparse
from networkx.readwrite import json_graph
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import GraphConfig
from src.graph_builder import SchemaGraphBuilder

def parse_args():
    parser = argparse.ArgumentParser(description="GRASP-SQL Graph Builder")
    parser.add_argument("--input_dir", type=str, default=GraphConfig.INPUT_ROOT,
                        help="Path to databases folder")
    parser.add_argument("--output_dir", type=str, default=GraphConfig.OUTPUT_ROOT,
                        help="Output folder for graphs")
    return parser.parse_args()

def process_database(db_folder, input_root, output_root, config):
    db_path = config.get_db_path(input_root, db_folder)
    desc_dir = config.get_desc_dir(input_root, db_folder)
    
    if not os.path.exists(db_path):
        return False, "SQLite file not found"

    try:
        builder = SchemaGraphBuilder(db_folder, db_path, desc_dir, config)
        graph = builder.build()
        
        output_file = os.path.join(output_root, f"{db_folder}.json")
        data = json_graph.node_link_data(graph, edges="links")  # networkx < 3.0 uses 'links'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True, f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}"
    except Exception as e:
        return False, str(e)

def main():
    args = parse_args()
    config = GraphConfig()  # Load default config
     
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created output directory: {args.output_dir}")

    subdirs = [d for d in os.listdir(args.input_dir) if os.path.isdir(os.path.join(args.input_dir, d))]
    print(f"Found {len(subdirs)} databases")

    for db_folder in tqdm(subdirs, desc="Processing"):
        success, msg = process_database(db_folder, args.input_dir, args.output_dir, config)
        if not success:
            tqdm.write(f"Error in {db_folder}: {msg}")

if __name__ == "__main__":
    main()
