"""Utility functions for the Library skill catalog.

Provides programmatic access to library.yaml operations:
source URL parsing, catalog loading, entry listing/searching,
dependency resolution, and install directory lookup.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


def parse_source_url(source: str) -> dict[str, str]:
    """Parse a source reference into its components.

    Supports three formats:
    - Local path:   /absolute/path or ~/relative/path
    - GitHub browser URL: https://github.com/org/repo/blob/branch/path
    - GitHub raw URL: https://raw.githubusercontent.com/org/repo/branch/path

    Returns a dict describing the source type and components.
    Raises ValueError for unsupported formats.
    """
    if not source:
        raise ValueError("Source cannot be empty")

    # Local paths
    if source.startswith("/") or source.startswith("~"):
        parent = str(Path(source).parent)
        return {
            "type": "local",
            "path": source,
            "parent_dir": parent,
        }

    # GitHub browser URL
    browser_match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)", source
    )
    if browser_match:
        org, repo, branch, file_path = browser_match.groups()
        parent_dir = str(Path(file_path).parent)
        return {
            "type": "github",
            "org": org,
            "repo": repo,
            "branch": branch,
            "file_path": file_path,
            "parent_dir": parent_dir,
            "clone_url": f"https://github.com/{org}/{repo}.git",
        }

    # GitHub raw URL
    raw_match = re.match(
        r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)", source
    )
    if raw_match:
        org, repo, branch, file_path = raw_match.groups()
        parent_dir = str(Path(file_path).parent)
        return {
            "type": "github",
            "org": org,
            "repo": repo,
            "branch": branch,
            "file_path": file_path,
            "parent_dir": parent_dir,
            "clone_url": f"https://github.com/{org}/{repo}.git",
        }

    raise ValueError(f"Unsupported source format: {source}")


def load_catalog(path: str) -> dict[str, Any]:
    """Load and parse a library.yaml catalog file.

    Raises FileNotFoundError if the file doesn't exist.
    Raises yaml.YAMLError for invalid YAML.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Catalog file not found: {path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def list_entries(
    catalog: dict[str, Any], entry_type: str | None = None
) -> list[dict[str, Any]]:
    """List catalog entries, optionally filtered by type.

    Args:
        catalog: Parsed catalog dict (from load_catalog).
        entry_type: One of "skills", "agents", "prompts", or None for all.

    Returns:
        List of entry dicts, each annotated with "_type" field.
    """
    valid_types = ("skills", "agents", "prompts")
    library = catalog.get("library", {})

    if entry_type is not None:
        if entry_type not in valid_types:
            raise ValueError(
                f"Unknown entry type: {entry_type}. Must be one of {valid_types}"
            )
        return [
            {**entry, "_type": entry_type}
            for entry in library.get(entry_type, [])
        ]

    results = []
    for t in valid_types:
        for entry in library.get(t, []):
            results.append({**entry, "_type": t})
    return results


def search_entries(
    catalog: dict[str, Any], keyword: str
) -> list[dict[str, Any]]:
    """Search catalog entries by keyword (case-insensitive).

    Matches against name and description fields.
    """
    keyword_lower = keyword.lower()
    all_entries = list_entries(catalog)
    return [
        entry
        for entry in all_entries
        if keyword_lower in entry.get("name", "").lower()
        or keyword_lower in entry.get("description", "").lower()
    ]


def get_entry(
    catalog: dict[str, Any], name: str
) -> dict[str, Any] | None:
    """Get a single entry by name across all types.

    Returns the entry dict with "_type" annotation, or None if not found.
    """
    for entry in list_entries(catalog):
        if entry["name"] == name:
            return entry
    return None


def resolve_dependencies(
    catalog: dict[str, Any], name: str
) -> list[dict[str, Any]]:
    """Resolve all dependencies for an entry, recursively and in order.

    Dependencies are listed before the items that depend on them.
    Raises ValueError if a dependency is not found in the catalog.
    """
    entry = get_entry(catalog, name)
    if entry is None:
        raise ValueError(f"Entry '{name}' not found in catalog")

    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _resolve(entry_name: str) -> None:
        if entry_name in seen:
            return
        seen.add(entry_name)

        current = get_entry(catalog, entry_name)
        if current is None:
            raise ValueError(
                f"Dependency '{entry_name}' not found in catalog"
            )

        requires = current.get("requires", [])
        for ref in requires:
            # Parse typed reference like "skill:name" or "agent:name"
            if ":" in ref:
                _, dep_name = ref.split(":", 1)
            else:
                dep_name = ref
            _resolve(dep_name)

        # Don't include the originally requested entry in its own deps
        if entry_name != name:
            resolved.append(current)

    _resolve(name)
    return resolved


def get_install_dir(
    catalog: dict[str, Any],
    entry_type: str,
    scope: str = "default",
    custom_path: str | None = None,
) -> str:
    """Determine the install directory for a given entry type.

    Args:
        catalog: Parsed catalog dict.
        entry_type: One of "skills", "agents", "prompts".
        scope: "default" or "global".
        custom_path: If provided, returned directly.

    Returns:
        The resolved directory path.
    """
    if custom_path is not None:
        return custom_path

    default_dirs = catalog.get("default_dirs", {})
    type_dirs = default_dirs.get(entry_type)
    if type_dirs is None:
        raise ValueError(
            f"Unknown entry type: {entry_type}. "
            f"Available: {list(default_dirs.keys())}"
        )

    for dir_entry in type_dirs:
        if scope in dir_entry:
            return dir_entry[scope]

    raise ValueError(
        f"Scope '{scope}' not found for type '{entry_type}'"
    )
