import json
import networkx as nx
from networkx.algorithms.approximation import steiner_tree
from config.runtime import LinkingSettings

def load_networkx_graph(json_path: str, config: LinkingSettings | None = None):
    if not json_path:
        return None, {}
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    G = nx.Graph()
    id_map = {}

    for node in data["nodes"]:
        real_id = node["id"]
        G.add_node(real_id, **node)

        if node["type"] == "column":
            keys = {
                real_id, 
                real_id.replace("`", "").strip(),
                node.get("name", "").strip().lower()
            }
            # Add table.column combinations
            t = node.get("table", "").strip()
            c = node.get("name", "").strip()
            o = node.get("original_column_name", "").strip()
            
            if t and c:
                keys.add(f"{t}.{c}".lower())
            if t and o:
                keys.add(f"{t}.{o}".lower())
            
            for k in keys:
                id_map[k] = real_id

    config = config or LinkingSettings()
    for link in data["links"]:
        ltype = link["type"]
        w = 1.0
        if ltype == "foreign_key":
            w = config.foreign_key_weight
        elif ltype == "structure":
            w = config.structure_weight
        elif ltype in {"similarity", "semantic"}:
            w = config.similarity_weight
        G.add_edge(link["source"], link["target"], weight=w, type=ltype)

    return G, id_map

def run_steiner_tree(G, terminals):
    valid_terminals = [n for n in terminals if G.has_node(n)]
    if not valid_terminals:
        return []
    
    if len(valid_terminals) == 1:
        node = valid_terminals[0]
        res = {node}
        for nb in G.neighbors(node):
            if G.nodes[nb].get("type") == "table":
                res.add(nb)
        return list(res)

    try:
        subtree = steiner_tree(G, valid_terminals, weight="weight")
        return list(subtree.nodes())
    except Exception:
        nodes = set(valid_terminals)
        root = valid_terminals[0]
        for t in valid_terminals[1:]:
            try:
                path = nx.shortest_path(G, root, t, weight="weight")
                nodes.update(path)
            except nx.NetworkXNoPath:
                pass
        return list(nodes)
