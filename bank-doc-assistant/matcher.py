from typing import Dict, List, Tuple, Any


def match(columns: List[str], docs: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Exact case-insensitive matching only. No fuzzy matching.

    Returns:
        documented  – dict keyed by *original* column name -> DocEntry
        undocumented – list of original column names with no doc match
    """
    documented: Dict[str, Any] = {}
    undocumented: List[str] = []

    for col in columns:
        key = col.strip().lower()
        if key in docs:
            documented[col] = docs[key]
        else:
            undocumented.append(col)

    return documented, undocumented
