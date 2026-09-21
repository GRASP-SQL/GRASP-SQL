import os
from dataclasses import dataclass

@dataclass
class GraphConfig:
    JACCARD_THRESHOLD: float = 0.6  # Similarity thresholds
    
    SAMPLE_LIMIT: int = 2          # Top N frequent examples
    SAMPLE_POOL_SIZE: int = 10000  # Pool size for sampling
    MAX_TEXT_LENGTH: int = 256     # Truncate length
    STRUCTURE_WEIGHT: float = 0.1
    FOREIGN_KEY_WEIGHT: float = 0.2
    SEMANTIC_WEIGHT: float = 1.0
    
    INPUT_ROOT: str = "./data/databases"
    OUTPUT_ROOT: str = "./schema_graphs/full"

    @staticmethod
    def get_db_path(root_dir: str, db_id: str) -> str:
        return os.path.join(root_dir, db_id, f"{db_id}.sqlite")

    @staticmethod
    def get_desc_dir(root_dir: str, db_id: str) -> str:
        return os.path.join(root_dir, db_id, "database_description")

@dataclass
class SubgraphConfig:
    DATA_PATH: str = "./data/example.json"
    GRAPH_ROOT: str = GraphConfig.OUTPUT_ROOT
    OUTPUT_PATH: str = "./schema_graphs/sub/example.jsonl"

    API_KEY: str = "sk-"
    BASE_URL: str = "https://api.deepseek.com"
    MODEL_NAME: str = "deepseek-chat"
    MAX_RETRIES: int = 3
    TEMPERATURE: float = 0.1

    # Weights for different edge types in Steiner Tree
    WEIGHT_FK: float = 0.1         # Foreign Key
    WEIGHT_STRUCT: float = 0.2     # Table-Column link
    WEIGHT_SIMILARITY: float = 2.0 # Semantic Similarity
    
    @staticmethod
    def get_db_graph_path(graph_root, db_id):
        return os.path.join(graph_root, f"{db_id}.json")
