"""Synthetic release-gate tests; no live GitHub CI or publication is simulated as evidence."""

import importlib.util
import io
import json
import re
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "afterforge_release_gate", Path(__file__).resolve().parents[1] / "scripts/plugin_release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


@pytest.fixture
def distribution(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    files = {name: "Synthetic fixture\n" for name in release.FILES}
    files["pyproject.toml"] = '[project]\nname = "agent-fix-lab"\nversion = "0.5.0"\n'
    files["packaging/plugin-readme.md"] = "Synthetic native readme\n"
    files["src/agent_fix_lab/example.py"] = "# Synthetic fixture\n"
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    release.git(repo, "init", "-q")
    release.git(repo, "add", ".")
    release.git(
        repo,
        "-c",
        "user.name=Synthetic fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Synthetic source",
    )
    source = release.git(repo, "rev-parse", "HEAD").decode().strip()
    output = tmp_path / "distribution"
    release.export(repo, source, output, "fixture/fork")
    sha = release.commit(repo, source, output)
    return repo, source, output, sha


def mock_ci(monkeypatch, source, changes=None):
    """Explicit mock API responses exercise rejection logic, not actual CI evidence."""
    monkeypatch.setenv("GH_TOKEN", "synthetic-test-only")

    def response(request, timeout):
        assert timeout == 30
        workflow = "validation" if request.full_url.endswith("/1") else "native-plugin"
        data = {
            "head_sha": source,
            "status": "completed",
            "conclusion": "success",
            "path": f".github/workflows/{workflow}.yml",
            "event": "push",
            "repository": {"full_name": "fixture/fork"},
            "head_repository": {"full_name": "fixture/fork"},
            "html_url": f"https://example.invalid/synthetic/{workflow}",
        }
        data.update(changes or {})
        return io.BytesIO(json.dumps(data).encode())

    monkeypatch.setattr(release.urllib.request, "urlopen", response)


def test_fork_manifest_and_reproducible_export(distribution, tmp_path):
    repo, source, output, sha = distribution
    again = tmp_path / "again"
    release.export(repo, source, again, "fixture/fork")
    assert release.commit(repo, source, again) == sha
    manifest = json.loads((output / "RELEASE.json").read_text())
    assert manifest["source_repository"] == "https://github.com/fixture/fork"
    assert manifest["version"] == "0.5.0"


def test_exact_distribution_and_both_checks_required(distribution, monkeypatch):
    repo, source, _, sha = distribution
    mock_ci(monkeypatch, source)
    monkeypatch.setattr(release, "native_distribution_sha", lambda *args: sha)
    result = release.stable_locator(repo, sha, "fixture/fork", "1", "2")
    assert result["source_commit"] == source
    assert result["distribution_commit"] == sha
    assert result["version"] == "0.5.0"
    assert set(result["ci"]) == {"application", "native"}
    assert "RELEASE.json" in result["checksums"]
    monkeypatch.setattr(release, "native_distribution_sha", lambda *args: "0" * 40)
    with pytest.raises(ValueError, match="exact native-tested"):
        release.stable_locator(repo, sha, "fixture/fork", "1", "2")


@pytest.mark.parametrize(
    "changes",
    [
        {"head_sha": "0" * 40},
        {"status": "in_progress"},
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"path": ".github/workflows/other.yml"},
        {"event": "pull_request"},
        {"repository": {"full_name": "other/repository"}},
        {"head_repository": {"full_name": "other/fork"}},
    ],
)
def test_ci_rejects_wrong_or_unfinished_evidence(distribution, monkeypatch, changes):
    _, source, _, _ = distribution
    mock_ci(monkeypatch, source, changes)
    with pytest.raises(ValueError, match="exact-source"):
        release.successful_run("fixture/fork", "1", source, "validation")


def test_tampered_distribution_rejected_before_ci(distribution):
    repo, source, output, _ = distribution
    (output / "src/agent_fix_lab/example.py").write_text("# Modified fixture\n")
    changed = release.commit(repo, source, output)
    with pytest.raises(ValueError, match="committed source"):
        release.stable_locator(repo, changed, "fixture/fork", "1", "2")


def test_unexpected_distribution_file_rejected(distribution):
    repo, source, output, _ = distribution
    (output / "extra.txt").write_text("Synthetic extra file\n")
    changed = release.commit(repo, source, output)
    with pytest.raises(ValueError, match="Unexpected"):
        release.stable_locator(repo, changed, "fixture/fork", "1", "2")


def test_repository_mismatch_rejected(distribution):
    repo, _, _, sha = distribution
    with pytest.raises(ValueError, match="repository mismatch"):
        release.stable_locator(repo, sha, "other/repository", "1", "2")


def test_repository_slug(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "fixture/renamed")
    assert release.repository_slug() == "fixture/renamed"
    for bad in ("https://github.com/a/b", "a/b/c", "a/b\n", "--option"):
        with pytest.raises(ValueError):
            release.repository_slug(bad)


def test_native_artifact_download_failure_is_not_certification(monkeypatch):
    def unavailable(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "gh")

    monkeypatch.setattr(release.subprocess, "run", unavailable)
    with pytest.raises(subprocess.CalledProcessError):
        release.native_distribution_sha("fixture/fork", "2")


def test_omitted_runtime_file_cannot_be_certified(distribution):
    repo, source, output, _ = distribution
    manifest_path = output / "RELEASE.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["files"]["src/agent_fix_lab/example.py"]
    manifest_path.write_text(json.dumps(manifest))
    (output / "src/agent_fix_lab/example.py").unlink()
    changed = release.commit(repo, source, output)
    with pytest.raises(ValueError, match="Incomplete source projection"):
        release.stable_locator(repo, changed, "fixture/fork", "1", "2")


def test_current_documentation_relative_links():
    root = Path(__file__).resolve().parents[1]
    docs = list((root / "docs").glob("*.md")) + [
        root / name for name in ("README.md", "SPEC.md", "devplan.md", "handoff.md", "CHANGELOG.md")
    ]
    for document in docs:
        for link in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            assert (document.parent / link.split("#")[0]).is_file(), (document.name, link)
