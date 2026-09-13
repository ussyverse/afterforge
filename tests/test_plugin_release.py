import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/plugin_release.py"
spec = importlib.util.spec_from_file_location("release_builder", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_committed_reproducible_release_and_source_integrity(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    files = {name: "synthetic\n" for name in release.FILES}
    files.update(
        {
            "packaging/plugin-readme.md": "Runtime guide\n",
            "src/agent_fix_lab/runner.py": 'print("all code shipped")\n',
            "src/agent_fix_lab/assets/app.js": 'console.log("asset");\n',
            "hermes_plugin/runtime.py": "# backend\n",
            "skills/workflow/SKILL.md": "Workflow\n",
            "tests/test_security.py": "# retained in development tree\n",
        }
    )
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "source",
    )
    sha = git("rev-parse", "HEAD")
    (repo / "src/agent_fix_lab/runner.py").write_text("UNCOMMITTED_PRIVATE\n")
    before = git("status", "--porcelain")
    first, second = tmp_path / "one", tmp_path / "two"
    release.export(repo, sha, first)
    release.export(repo, sha, second)
    assert (first / "src/agent_fix_lab/runner.py").read_text() == files[
        "src/agent_fix_lab/runner.py"
    ]
    assert not (first / "tests").exists()
    assert (repo / "tests/test_security.py").exists()
    assert (first / "RELEASE.json").read_bytes() == (second / "RELEASE.json").read_bytes()
    assert json.loads((first / "RELEASE.json").read_text())["source_commit"] == sha
    one = release.commit(repo, sha, first)
    assert one == release.commit(repo, sha, second)
    assert git("status", "--porcelain") == before
    assert (
        git("show", f"{one}:src/agent_fix_lab/runner.py")
        == files["src/agent_fix_lab/runner.py"].strip()
    )
    with pytest.raises(ValueError, match="empty"):
        release.export(repo, sha, first)
