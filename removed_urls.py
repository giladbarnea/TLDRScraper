import json
from pathlib import Path
from typing import Set

REMOVED_URLS_FILENAME = "removed_urls.json"
REMOVED_URLS_FILE = Path(REMOVED_URLS_FILENAME)


def get_removed_urls() -> Set[str]:
    data = json.loads(REMOVED_URLS_FILE.read_text())
    return set(data)


def add_removed_url(url: str) -> bool:
    removed = get_removed_urls()
    removed.add(url)
    REMOVED_URLS_FILE.write_text(
        json.dumps(sorted(removed), indent=2)
    )
    return True
