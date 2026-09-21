import sqlite3
from itertools import combinations

import networkx as nx
from config.settings import GraphConfig
from src.utils.text import calculate_cosine_similarity
from src.utils.db import load_csv_descriptions, get_column_examples

class SchemaGraphBuilder:
    def __init__(self, db_name: str, db_path: str, desc_dir: str, config: GraphConfig):
        self.db_name = db_name
        self.db_path = db_path
        self.desc_dir = desc_dir
        self.cfg = config
        self.G = nx.Graph()
        self.descriptions = load_csv_descriptions(desc_dir)

    def _add_table_nodes(self, cursor, tables):
        """Adds table nodes and column nodes with structure edges."""
        column_nodes = []
        
        for table in tables:
            t_node_id = str(table)
            self.G.add_node(t_node_id, type="table", name=table)
            
            cursor.execute(f"PRAGMA table_info({self._quote_identifier(table)})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_pk = (col[5] == 1)
                
                # Metadata enrichment
                desc_key = (table, col_name)
                meta_data = self.descriptions.get(desc_key, {})
                
                # Data sampling
                examples = get_column_examples(
                    cursor, table, col_name, 
                    self.cfg.SAMPLE_POOL_SIZE, self.cfg.SAMPLE_LIMIT, self.cfg.MAX_TEXT_LENGTH
                )

                # Node construction
                c_node_id = f"{table}.{col_name}"
                
                self.G.add_node(
                    c_node_id,
                    type="column",
                    table=table,
                    name=col_name,
                    col_type=col_type,
                    is_pk=is_pk,
                    examples=examples,
                    descriptor=self._descriptor(table, col_name, col_type, is_pk, meta_data),
                    **meta_data
                )
                column_nodes.append(c_node_id)
                self.G.add_edge(
                    t_node_id, c_node_id, type="structure", weight=self.cfg.STRUCTURE_WEIGHT
                )
        
        return column_nodes

    def _add_foreign_keys(self, cursor, tables):
        """Adds edges representing foreign keys."""
        for table in tables:
            cursor.execute(f"PRAGMA foreign_key_list({self._quote_identifier(table)})")
            for fk in cursor.fetchall():
                target_table, source_col, target_col = fk[2], fk[3], fk[4]
                src_node = f"{table}.{source_col}"
                tgt_node = f"{target_table}.{target_col}"
                
                if self.G.has_node(src_node) and self.G.has_node(tgt_node):
                    self.G.add_edge(
                        src_node, tgt_node, type="foreign_key", weight=self.cfg.FOREIGN_KEY_WEIGHT
                    )

    def _add_semantic_edges(self, column_nodes):
        """Adds cosine-similarity edges over serialized column descriptors."""
        for n1, n2 in combinations(column_nodes, 2):
            node1 = self.G.nodes[n1]
            node2 = self.G.nodes[n2]
            
            # Skip same table or existing structural edges
            if node1['table'] == node2['table'] or self.G.has_edge(n1, n2):
                continue
            
            score = calculate_cosine_similarity(node1['descriptor'], node2['descriptor'])
            if score >= self.cfg.JACCARD_THRESHOLD:
                self.G.add_edge(
                    n1, n2, type="semantic", similarity=score, weight=self.cfg.SEMANTIC_WEIGHT
                )

    @staticmethod
    def _quote_identifier(identifier):
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _descriptor(table, column, column_type, is_pk, metadata):
        details = [table, column, column_type or "", "primary key" if is_pk else ""]
        for key in ("column_description", "value_description"):
            if metadata.get(key):
                details.append(str(metadata[key]))
        return " ".join(details)

    def build(self) -> nx.Graph:
        """Main execution pipeline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            col_nodes = self._add_table_nodes(cursor, tables)
            self._add_foreign_keys(cursor, tables)
            self._add_semantic_edges(col_nodes)
            
        finally:
            conn.close()
            
        return self.G
