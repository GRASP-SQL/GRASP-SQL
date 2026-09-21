from src.utils.graph import run_steiner_tree

class SubgraphExtractor:
    def map_to_graph_ids(self, raw_names, id_map):
        real_ids = set()
        for raw in raw_names:
            key = raw.strip().lower()
            if key in id_map:
                real_ids.add(id_map[key])
            else:
                key_clean = key.replace("`", "")
                if key_clean in id_map:
                    real_ids.add(id_map[key_clean])
        return list(real_ids)

    def process(self, G, id_map, raw_column_names):
        terminals = self.map_to_graph_ids(raw_column_names, id_map)
        sub_node_ids = run_steiner_tree(G, terminals)
        
        final_cols = []
        seen_tables = set()
        foreign_keys = []
        sub_set = set(sub_node_ids)

        for nid in sub_node_ids:
            node_data = G.nodes[nid]
            if node_data["type"] == "column":
                final_cols.append(node_data)
                seen_tables.add(node_data["table"])
            elif node_data["type"] == "table":
                seen_tables.add(node_data["name"])

        for u, v, data in G.edges(data=True):
            if data["type"] == "foreign_key" and u in sub_set and v in sub_set:
                foreign_keys.append({"source": u, "target": v})

        return {
            "tables": list(seen_tables),
            "columns": final_cols,
            "foreign_keys": foreign_keys
        }
