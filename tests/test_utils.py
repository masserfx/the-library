"""Tests for library utility functions."""

import os
import tempfile
import pytest

from utils import (
    parse_source_url,
    load_catalog,
    list_entries,
    search_entries,
    get_entry,
    resolve_dependencies,
    get_install_dir,
)


# ---------------------------------------------------------------------------
# parse_source_url
# ---------------------------------------------------------------------------

class TestParseSourceUrl:
    """Test source URL parsing for local, GitHub browser, and raw URLs."""

    def test_local_absolute_path(self):
        result = parse_source_url("/Users/me/projects/skills/my-skill/SKILL.md")
        assert result == {
            "type": "local",
            "path": "/Users/me/projects/skills/my-skill/SKILL.md",
            "parent_dir": "/Users/me/projects/skills/my-skill",
        }

    def test_local_tilde_path(self):
        result = parse_source_url("~/projects/skills/my-skill/SKILL.md")
        assert result["type"] == "local"
        assert result["path"] == "~/projects/skills/my-skill/SKILL.md"
        assert result["parent_dir"] == "~/projects/skills/my-skill"

    def test_github_browser_url(self):
        url = "https://github.com/myorg/repo/blob/main/skills/foo/SKILL.md"
        result = parse_source_url(url)
        assert result == {
            "type": "github",
            "org": "myorg",
            "repo": "repo",
            "branch": "main",
            "file_path": "skills/foo/SKILL.md",
            "parent_dir": "skills/foo",
            "clone_url": "https://github.com/myorg/repo.git",
        }

    def test_github_browser_url_nested_branch(self):
        url = "https://github.com/org/repo/blob/feature/v2/path/to/SKILL.md"
        result = parse_source_url(url)
        # The parser takes everything after 'blob/' up to the next '/' as branch
        # This is a known limitation — single-segment branches only
        assert result["type"] == "github"
        assert result["org"] == "org"
        assert result["repo"] == "repo"

    def test_github_raw_url(self):
        url = "https://raw.githubusercontent.com/myorg/repo/main/skills/foo/SKILL.md"
        result = parse_source_url(url)
        assert result == {
            "type": "github",
            "org": "myorg",
            "repo": "repo",
            "branch": "main",
            "file_path": "skills/foo/SKILL.md",
            "parent_dir": "skills/foo",
            "clone_url": "https://github.com/myorg/repo.git",
        }

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Unsupported source format"):
            parse_source_url("ftp://example.com/foo")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_source_url("")


# ---------------------------------------------------------------------------
# load_catalog
# ---------------------------------------------------------------------------

class TestLoadCatalog:
    """Test YAML catalog loading."""

    def test_load_valid_catalog(self, tmp_path):
        catalog_file = tmp_path / "library.yaml"
        catalog_file.write_text(
            "default_dirs:\n"
            "  skills:\n"
            "    - default: .claude/skills/\n"
            "library:\n"
            "  skills:\n"
            "    - name: foo\n"
            "      description: A foo skill\n"
            "      source: /path/to/foo/SKILL.md\n"
            "  agents: []\n"
            "  prompts: []\n"
        )
        catalog = load_catalog(str(catalog_file))
        assert "library" in catalog
        assert len(catalog["library"]["skills"]) == 1
        assert catalog["library"]["skills"][0]["name"] == "foo"

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_catalog("/nonexistent/path/library.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(": invalid: yaml: [")
        with pytest.raises(Exception):
            load_catalog(str(bad_file))


# ---------------------------------------------------------------------------
# list_entries
# ---------------------------------------------------------------------------

class TestListEntries:
    """Test listing catalog entries."""

    def _make_catalog(self):
        return {
            "library": {
                "skills": [
                    {"name": "alpha", "description": "Alpha skill", "source": "/a"},
                    {"name": "beta", "description": "Beta skill", "source": "/b"},
                ],
                "agents": [
                    {"name": "agent-one", "description": "Agent", "source": "/c"},
                ],
                "prompts": [],
            }
        }

    def test_list_all(self):
        entries = list_entries(self._make_catalog())
        assert len(entries) == 3

    def test_list_by_type(self):
        entries = list_entries(self._make_catalog(), entry_type="skills")
        assert len(entries) == 2
        assert all(e["_type"] == "skills" for e in entries)

    def test_list_agents(self):
        entries = list_entries(self._make_catalog(), entry_type="agents")
        assert len(entries) == 1
        assert entries[0]["name"] == "agent-one"

    def test_list_empty_type(self):
        entries = list_entries(self._make_catalog(), entry_type="prompts")
        assert entries == []

    def test_list_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown entry type"):
            list_entries(self._make_catalog(), entry_type="widgets")


# ---------------------------------------------------------------------------
# search_entries
# ---------------------------------------------------------------------------

class TestSearchEntries:
    """Test keyword search across catalog entries."""

    def _make_catalog(self):
        return {
            "library": {
                "skills": [
                    {"name": "python-testing", "description": "Python testing patterns", "source": "/a"},
                    {"name": "shadcn-ui", "description": "shadcn/ui component library", "source": "/b"},
                    {"name": "tailwind-theme", "description": "Tailwind CSS theme builder", "source": "/c"},
                ],
                "agents": [],
                "prompts": [],
            }
        }

    def test_search_by_name(self):
        results = search_entries(self._make_catalog(), "python")
        assert len(results) == 1
        assert results[0]["name"] == "python-testing"

    def test_search_by_description(self):
        results = search_entries(self._make_catalog(), "component")
        assert len(results) == 1
        assert results[0]["name"] == "shadcn-ui"

    def test_search_case_insensitive(self):
        results = search_entries(self._make_catalog(), "TAILWIND")
        assert len(results) == 1

    def test_search_no_match(self):
        results = search_entries(self._make_catalog(), "nonexistent")
        assert results == []

    def test_search_multiple_matches(self):
        results = search_entries(self._make_catalog(), "th")  # matches "theme" and "python-testing" (no), "theme" in tailwind
        # "th" appears in "tailwind-theme" (name) and "theme builder" (desc)
        assert any(r["name"] == "tailwind-theme" for r in results)


# ---------------------------------------------------------------------------
# get_entry
# ---------------------------------------------------------------------------

class TestGetEntry:
    """Test retrieving a specific entry by name."""

    def _make_catalog(self):
        return {
            "library": {
                "skills": [
                    {"name": "foo", "description": "Foo", "source": "/foo"},
                    {"name": "bar", "description": "Bar", "source": "/bar"},
                ],
                "agents": [
                    {"name": "baz", "description": "Baz", "source": "/baz"},
                ],
                "prompts": [],
            }
        }

    def test_get_existing_skill(self):
        entry = get_entry(self._make_catalog(), "foo")
        assert entry is not None
        assert entry["name"] == "foo"
        assert entry["_type"] == "skills"

    def test_get_existing_agent(self):
        entry = get_entry(self._make_catalog(), "baz")
        assert entry is not None
        assert entry["_type"] == "agents"

    def test_get_nonexistent_returns_none(self):
        entry = get_entry(self._make_catalog(), "nonexistent")
        assert entry is None


# ---------------------------------------------------------------------------
# resolve_dependencies
# ---------------------------------------------------------------------------

class TestResolveDependencies:
    """Test dependency resolution for typed references."""

    def _make_catalog(self):
        return {
            "library": {
                "skills": [
                    {"name": "base", "description": "Base", "source": "/base"},
                    {
                        "name": "advanced",
                        "description": "Advanced",
                        "source": "/adv",
                        "requires": ["skill:base"],
                    },
                    {
                        "name": "mega",
                        "description": "Mega",
                        "source": "/mega",
                        "requires": ["skill:advanced", "agent:helper"],
                    },
                ],
                "agents": [
                    {"name": "helper", "description": "Helper", "source": "/helper"},
                ],
                "prompts": [],
            }
        }

    def test_no_dependencies(self):
        deps = resolve_dependencies(self._make_catalog(), "base")
        assert deps == []

    def test_single_dependency(self):
        deps = resolve_dependencies(self._make_catalog(), "advanced")
        assert len(deps) == 1
        assert deps[0]["name"] == "base"

    def test_transitive_dependencies(self):
        deps = resolve_dependencies(self._make_catalog(), "mega")
        names = [d["name"] for d in deps]
        assert "base" in names
        assert "advanced" in names
        assert "helper" in names

    def test_dependency_order(self):
        """Dependencies should be listed before the items that depend on them."""
        deps = resolve_dependencies(self._make_catalog(), "mega")
        names = [d["name"] for d in deps]
        assert names.index("base") < names.index("advanced")

    def test_missing_dependency_raises(self):
        catalog = {
            "library": {
                "skills": [
                    {"name": "broken", "description": "Broken", "source": "/x", "requires": ["skill:nonexistent"]},
                ],
                "agents": [],
                "prompts": [],
            }
        }
        with pytest.raises(ValueError, match="not found"):
            resolve_dependencies(catalog, "broken")


# ---------------------------------------------------------------------------
# get_install_dir
# ---------------------------------------------------------------------------

class TestGetInstallDir:
    """Test install directory resolution."""

    def _make_catalog(self):
        return {
            "default_dirs": {
                "skills": [
                    {"default": ".claude/skills/"},
                    {"global": "~/.claude/skills/"},
                ],
                "agents": [
                    {"default": ".claude/agents/"},
                    {"global": "~/.claude/agents/"},
                ],
                "prompts": [
                    {"default": ".claude/commands/"},
                    {"global": "~/.claude/commands/"},
                ],
            }
        }

    def test_default_dir(self):
        result = get_install_dir(self._make_catalog(), "skills")
        assert result == ".claude/skills/"

    def test_global_dir(self):
        result = get_install_dir(self._make_catalog(), "skills", scope="global")
        assert result == "~/.claude/skills/"

    def test_custom_dir(self):
        result = get_install_dir(self._make_catalog(), "skills", custom_path="/my/path/")
        assert result == "/my/path/"

    def test_agents_default(self):
        result = get_install_dir(self._make_catalog(), "agents")
        assert result == ".claude/agents/"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            get_install_dir(self._make_catalog(), "widgets")
