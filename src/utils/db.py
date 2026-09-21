import os
import sqlite3
import pandas as pd
from collections import Counter
from typing import List, Dict, Any, Optional

def load_csv_descriptions(desc_dir: str) -> Dict[tuple, Dict]:
    """Loads column descriptions from CSV files in the directory."""
    descriptions = {}
    if not os.path.exists(desc_dir):
        return descriptions

    for filename in os.listdir(desc_dir):
        if not filename.endswith(".csv"):
            continue
            
        table_name = filename.replace(".csv", "").strip()
        csv_path = os.path.join(desc_dir, filename)
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df = df.astype(object).where(pd.notnull(df), None)
            df.columns = [c.strip() for c in df.columns]
            
            for _, row in df.iterrows():
                orig_col = row.get('original_column_name')
                if orig_col:
                    row_dict = row.to_dict()
                    clean_dict = {
                        k: (None if pd.isna(v) else v)
                        for k, v in row_dict.items()
                    }
                    descriptions[(table_name, orig_col.strip())] = clean_dict
        except Exception:
            continue  # Skip malformed CSVs
            
    return descriptions

def get_column_examples(cursor: sqlite3.Cursor, table: str, col: str, 
                       pool_size: int, limit: int, max_len: int) -> List[str]:
    """Fetches top frequent non-null values from a column."""
    try:
        query = f'SELECT `{col}` FROM `{table}` WHERE `{col}` IS NOT NULL LIMIT {pool_size}'
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            return []

        valid_values = []
        for r in rows:
            val = r[0]
            if val is None:
                continue
            
            val_str = str(val).strip()
            if not val_str:
                continue
            
            if len(val_str) > max_len:
                val_str = val_str[:max_len] + "..."
            valid_values.append(val_str)
        
        if not valid_values:
            return []

        # Return top N most common values
        counts = Counter(valid_values).most_common(limit)
        return [item[0] for item in counts]

    except Exception:
        return []
