import tomllib
from pathlib import Path


def load_targets() -> list[dict]:
    path = Path("config/product_targets.toml")
    if not path.exists():
        return []
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("targets", [])


TARGETS = load_targets()

def get_search_terms() -> list[str]:
    terms = []
    for t in TARGETS:
        terms.extend(t.get("search_terms", []))
    return list(set(terms))


SEARCH_TERMS = get_search_terms()

def get_price_ceiling(category: str) -> float:
    for t in TARGETS:
        if t["category"] == category:
            return t["max_price"]
    return 0.0

def get_max_price_for_product(product_title: str) -> float:
    title_lower = product_title.lower()
    for t in TARGETS:
        for term in t.get("search_terms", []):
            if term.lower() in title_lower:
                return t["max_price"]
    return 0.0
