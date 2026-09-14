# Legacy profile-local skill integration — 0.5.0

For native Afterforge aliases and managed locked setup use [native-plugin.md](native-plugin.md). This page describes the retained older editable skill, not a second native plugin. Do not install both merely to rename the product. Existing data/environments are preserved; see [migration](migration.md).

Use the running profile's resolved HERMES_HOME. Do not append `profiles/default`: this installation has already resolved its home. Discovery inspected schema 26 and installed source commit 277268d; release-directory names are not assumed to be commit identity. The original private discovery record holds resolved paths/version details.

Hermes messages use session/message/tool-call IDs, Unix-second timestamps, archived flags and message compacted state. Parent sessions represent ancestry; the inspected delegation metadata uses `_delegate_from`. Import consults actual schema columns and does not construct a Hermes writer. Official references: https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage/ and https://hermes-agent.nousresearch.com/docs/skills/.

## Installation

From the public source checkout, in an isolated environment:

```sh
uv sync --locked
uv build
uv venv "$HERMES_HOME/venvs/agent-fix-lab"
uv pip install --python "$HERMES_HOME/venvs/agent-fix-lab/bin/python" dist/agent_fix_lab-0.5.0-py3-none-any.whl
python3 scripts/install_hermes.py --hermes-home "$HERMES_HOME" --lab-home "$AGENT_FIX_LAB_HOME" --executable "$HERMES_HOME/venvs/agent-fix-lab/bin/agent-fix-lab"
python3 "$HERMES_HOME/skills/agent-fix-lab/scripts/lab.py" doctor
```

The installer creates only `skills/agent-fix-lab/{SKILL.md,installation.json,scripts/lab.py}` in the chosen home. The local installation file contains resolved private paths and must not be committed. Existing paths are not overwritten.

Hermes loads the supported skill with `skill_view(name='agent-fix-lab')`. The skill tells its existing terminal tool to invoke the wrapper. This is a real supported skill integration, not an invented slash command or custom model replay tool. The installed loader returned success and readiness `available` during development.

Wrapper commands: `doctor`, `find QUERY`, `inspect CASE_ID`, `import AFTER_UNIX_SECONDS`, `run REVIEWED_RECIPE_ID`, `report CASE_ID`. Exactly one bounded argument is accepted where required. Import is limited to 100 records and explicitly uses the dogfood cohort; use the full CLI for pagination/selection. `run` cannot create or authorize recipes.

## Updating and removing

Build the new wheel, then `uv pip install --reinstall-package agent-fix-lab --python "$HERMES_HOME/venvs/agent-fix-lab/bin/python" dist/agent_fix_lab-0.5.0-py3-none-any.whl`. This legacy wheel route is not the native managed lock/generation guarantee. For a wrapper update, remove the owned skill and rerun the installer:

```sh
python3 scripts/install_hermes.py --remove --hermes-home "$HERMES_HOME"
```

Removal checks its ownership marker and removes only that skill directory. It preserves the package environment and all private data. The virtual environment can be deleted separately after confirming its path and stopping any Agent Fix Lab server. Never remove the Hermes environment. Neither operation changes Hermes prompts, SOUL.md, permissions, memories, schedules or code; no restart is required for CLI use.

Troubleshooting: use `doctor` for schema/source discovery, verify the wrapper installation file points to the intended executable/data home, and use a writable UV_CACHE_DIR if cache permissions block installation. If the current session's tool menu predates skill installation, the terminal wrapper remains directly usable; do not claim a newly registered API tool exists.
