import math
import re
from collections import Counter
from typing import Set

def tokenize(text: str) -> Set[str]:
    """Splits string into tokens, removing empty strings."""
    if not text:
        return set()
    tokens = set(re.split(r'[_\s]+', text.lower()))
    tokens.discard('')
    return tokens

def calculate_jaccard(str1: str, str2: str) -> float:
    """Calculates Jaccard similarity between two strings."""
    tokens1 = tokenize(str1)
    tokens2 = tokenize(str2)
    
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    return intersection / union if union > 0 else 0.0


def calculate_cosine_similarity(str1: str, str2: str) -> float:
    """Cosine similarity over schema-descriptor tokens.

    The graph must be self-contained and runnable without an embedding service.
    This sparse representation still uses the descriptor, not merely the column
    name, and gives semantic edges the highest traversal cost.
    """
    first = Counter(re.findall(r"[a-z0-9]+", str1.lower()))
    second = Counter(re.findall(r"[a-z0-9]+", str2.lower()))
    if not first or not second:
        return 0.0
    numerator = sum(first[token] * second[token] for token in first.keys() & second.keys())
    denominator = math.sqrt(sum(value * value for value in first.values())) * math.sqrt(
        sum(value * value for value in second.values())
    )
    return numerator / denominator if denominator else 0.0
