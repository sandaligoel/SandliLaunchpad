#!/usr/bin/env python3
"""List agents in the catalog index (no search, no relevance scores)."""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from server import configure_logging, get_settings

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Finance & Procurement",
    "Document & Data",
    "Quality & Compliance",
    "Supply Chain & Logistics",
    "Sales & Revenue",
    "Healthcare & Compliance",
]


def _fetch_all_agents(settings) -> list[dict]:
    """
    Retrieve every agent document from the index.

    Sorting is done in Python — ``name`` is searchable but not sortable on the index.
    """
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
    results = client.search(
        search_text="*",
        top=1000,
        select=[
            "id",
            "name",
            "version",
            "category",
            "status",
            "origin_client",
            "origin_project",
            "vertical",
        ],
    )
    agents = [dict(r) for r in results]
    agents.sort(key=lambda a: (a.get("name") or "").lower())
    return agents


def _status_label(status: str) -> str:
    return f"[{status:<9}]"


def main() -> None:
    """
    Print all indexed agents grouped by category.

    Does not run hybrid search or print relevance scores.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    agents = _fetch_all_agents(settings)

    if not agents:
        print("No agents found in index. Run:")
        print("  python scripts/create_index.py")
        print("  python -m pipeline.run --source ./data/spec.json")
        return

    by_category: dict[str, list[dict]] = defaultdict(list)
    by_status: dict[str, int] = defaultdict(int)
    by_vertical: dict[str, int] = defaultdict(int)

    for agent in agents:
        cat = agent.get("category") or "Uncategorized"
        by_category[cat].append(agent)
        by_status[agent.get("status") or "unknown"] += 1
        by_vertical[agent.get("vertical") or "unknown"] += 1

    print(f"\nTotal agents indexed: {len(agents)}\n")

    for category in CATEGORIES:
        group = by_category.get(category, [])
        if not group:
            continue
        print(f"=== {category} ({len(group)} agents) ===")
        for agent in sorted(group, key=lambda a: a.get("name", "")):
            status = _status_label(agent.get("status", "unknown"))
            name = agent.get("name", "Unknown")
            version = agent.get("version", "")
            client = agent.get("origin_client", "")
            project = agent.get("origin_project", "")
            version_str = f" v{version}" if version else ""
            print(f"  {status} {name}{version_str}")
            if client or project:
                print(f"           {client} — {project}")
        print()

    uncategorized = by_category.get("Uncategorized", [])
    if uncategorized:
        print(f"=== Uncategorized ({len(uncategorized)} agents) ===")
        for agent in uncategorized:
            print(f"  {agent.get('name')}")
        print()

    print("--- Breakdown ---")
    print("By status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    print("By vertical:")
    for vertical, count in sorted(by_vertical.items()):
        print(f"  {vertical}: {count}")


if __name__ == "__main__":
    main()
