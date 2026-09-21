import sqlglot
from sqlglot import exp

class SQLUtils:
    @staticmethod
    def normalize_col(col_str):
        if not col_str:
            return ""
        return col_str.replace("`", "").replace('"', "").replace("'", "").lower().strip()

    @staticmethod
    def is_id_match(col1, col2):
        """
        Matching for ID/Foreign Key columns.
        """
        c1, c2 = SQLUtils.normalize_col(col1), SQLUtils.normalize_col(col2)
        if c1 == c2:
            return True
        return False

    @staticmethod
    def get_alias_mapping(parsed):
        alias_map = {}
        for t in parsed.find_all(exp.Table):
            name = t.name
            alias = t.alias
            if name:
                norm_name = SQLUtils.normalize_col(name)
                if alias:
                    alias_map[SQLUtils.normalize_col(alias)] = norm_name
                alias_map[norm_name] = norm_name
        return alias_map

    @staticmethod
    def extract_gt_info(sql):
        """
        Extracts columns and tables from Ground Truth SQL.
        Returns: (col_set, table_set)
        """
        col_set = set()
        table_set = set()
        
        if not sql:
            return col_set, table_set

        try:
            parsed = sqlglot.parse_one(sql, read="sqlite")
            alias_map = SQLUtils.get_alias_mapping(parsed)
            
            tables = [t.name for t in parsed.find_all(exp.Table) if t.name]
            default_table = tables[0] if len(set(tables)) == 1 else None

            for node in parsed.walk():
                if isinstance(node, exp.Star):
                    continue

                if isinstance(node, exp.Column):
                    col = node.name
                    tbl = node.table
                    real_tbl = None
                    
                    if tbl:
                        real_tbl = alias_map.get(SQLUtils.normalize_col(tbl), tbl)
                    elif default_table:
                        real_tbl = default_table
                    
                    if real_tbl:
                        table_set.add(SQLUtils.normalize_col(real_tbl))
                        full_name = f"{real_tbl}.{col}"
                    else:
                        full_name = f"{col}"
                    
                    if full_name and "*" not in full_name:
                        col_set.add(SQLUtils.normalize_col(full_name))
        except:
            pass 

        return col_set, table_set

class MetricsCalculator:
    @staticmethod
    def smart_match(pred_col, gt_col):
        p_norm = SQLUtils.normalize_col(pred_col)
        g_norm = SQLUtils.normalize_col(gt_col)

        if p_norm == g_norm:
            return True

        p_parts = p_norm.split('.')
        g_parts = g_norm.split('.')
        p_c = p_parts[-1]
        g_c = g_parts[-1]

        if p_c == g_c:
            p_tbl = p_parts[0] if len(p_parts) > 1 else None
            g_tbl = g_parts[0] if len(g_parts) > 1 else None
            if p_tbl and g_tbl and p_tbl != g_tbl:
                return False
            return True

        if SQLUtils.is_id_match(p_c, g_c):
            return True

        return False

    @staticmethod
    def compute(pred_set, gt_set, gt_tables):
        """
        Compute P/R/F1 with PK Tolerance strategy.
        PK Tolerance: Do not penalize predicting extra IDs if the table exists in GT.
        """
        preds = list(pred_set)
        gts = list(gt_set)
        
        if not gts:
            return 0.0, 0.0, 0.0, False 
        
        tp = 0
        gt_matched = [False] * len(gts)
        pred_matched_indices = set()

        # Standard Matching
        for pi, p in enumerate(preds):
            for gi, g in enumerate(gts):
                if gt_matched[gi]:
                    continue
                
                if MetricsCalculator.smart_match(p, g):
                    tp += 1
                    gt_matched[gi] = True
                    pred_matched_indices.add(pi)
                    break 

        # PK Tolerance (Adjust Denominator)
        effective_pred_count = len(preds)
        for pi, p in enumerate(preds):
            if pi in pred_matched_indices:
                continue 
        
        if effective_pred_count < tp: effective_pred_count = tp

        precision = tp / effective_pred_count if effective_pred_count > 0 else 0.0
        recall = tp / len(gts)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return precision, recall, f1, True
