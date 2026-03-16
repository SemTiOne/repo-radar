"""
tests/test_bulk.py — Tests for cli/bulk.py
"""

import json
import pytest

from cli.bulk import (
    load_repos_from_file,
    load_repos_from_package_json,
    load_repos_from_requirements,
)


class TestLoadReposFromFile:
    def test_loads_valid_repos(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("user/repo-a\nuser/repo-b\n")
        repos = load_repos_from_file(str(f))
        assert "user/repo-a" in repos
        assert "user/repo-b" in repos

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("user/repo-a\n\n\nuser/repo-b\n")
        repos = load_repos_from_file(str(f))
        assert len(repos) == 2

    def test_skips_comment_lines(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("# This is a comment\nuser/repo-a\n# Another comment\nuser/repo-b\n")
        repos = load_repos_from_file(str(f))
        assert len(repos) == 2
        assert all(not r.startswith("#") for r in repos)

    def test_skips_invalid_urls(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("user/repo-a\nnot-a-valid-url\nhttps://gitlab.com/user/repo\n")
        repos = load_repos_from_file(str(f))
        assert len(repos) == 1
        assert repos[0] == "user/repo-a"

    def test_deduplicates_repos(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("user/repo\nuser/repo\nuser/repo\n")
        repos = load_repos_from_file(str(f))
        assert len(repos) == 1

    def test_handles_full_github_urls(self, tmp_path):
        f = tmp_path / "repos.txt"
        f.write_text("https://github.com/user/repo\n")
        repos = load_repos_from_file(str(f))
        assert len(repos) == 1


class TestLoadReposFromPackageJson:
    def test_extracts_github_shorthand_versions(self, tmp_path):
        pkg = {
            "dependencies": {
                "some-lib": "github:user/some-lib#main",
                "other-lib": "^1.0.0",
            }
        }
        f = tmp_path / "package.json"
        f.write_text(json.dumps(pkg))
        repos = load_repos_from_package_json(str(f))
        assert any("user/some-lib" in r for r in repos)

    def test_extracts_repository_field(self, tmp_path):
        pkg = {
            "dependencies": {},
            "repository": {
                "type": "git",
                "url": "https://github.com/user/myproject",
            },
        }
        f = tmp_path / "package.json"
        f.write_text(json.dumps(pkg))
        repos = load_repos_from_package_json(str(f))
        assert any("user/myproject" in r for r in repos)

    def test_handles_empty_dependencies(self, tmp_path):
        pkg = {"dependencies": {}, "devDependencies": {}}
        f = tmp_path / "package.json"
        f.write_text(json.dumps(pkg))
        repos = load_repos_from_package_json(str(f))
        assert repos == []


class TestLoadReposFromRequirements:
    def test_parses_github_url_in_requirements(self, tmp_path):
        f = tmp_path / "requirements.txt"
        f.write_text(
            "requests==2.31.0\n"
            "git+https://github.com/user/mylib@main#egg=mylib\n"
            "rich>=13.0.0\n"
        )
        repos = load_repos_from_requirements(str(f))
        assert any("user/mylib" in r for r in repos)

    def test_skips_standard_packages(self, tmp_path):
        f = tmp_path / "requirements.txt"
        f.write_text("requests==2.31.0\nrich>=13.0.0\nfastapi\n")
        repos = load_repos_from_requirements(str(f))
        assert repos == []

    def test_skips_comment_lines(self, tmp_path):
        f = tmp_path / "requirements.txt"
        f.write_text(
            "# This is a comment\n"
            "git+https://github.com/user/repo@main\n"
        )
        repos = load_repos_from_requirements(str(f))
        assert len(repos) == 1

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "requirements.txt"
        f.write_text("\n\ngit+https://github.com/user/repo@main\n\n")
        repos = load_repos_from_requirements(str(f))
        assert len(repos) == 1