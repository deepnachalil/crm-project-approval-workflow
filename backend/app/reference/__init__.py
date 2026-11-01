"""Configurable reference data (rate-card catalog, picklists).

Rate cards and standard job categories are seeded into the database from
catalog.json; the picklists are served directly from the file. Edit the JSON
(and re-run the seed) to change the catalog.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache
def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
