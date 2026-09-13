"""Stable argparse contract; all commands emit JSON except help and web serving."""

import argparse
import json
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

from .history import import_hermes, snapshot, validate_schema
from .service import Lab
from .store import Store


def default_home():
    return Path(os.environ.get("AGENT_FIX_LAB_HOME", Path.home() / ".local/share/agent-fix-lab"))


def parser():
    p = argparse.ArgumentParser(prog="agent-fix-lab")
    p.add_argument("--home", type=Path, default=default_home())
    commands = p.add_subparsers(dest="command", required=True)
    d = commands.add_parser("doctor")
    d.add_argument("--source", type=Path)
    i = commands.add_parser("import-hermes")
    i.add_argument("--source", type=Path, required=True)
    i.add_argument(
        "--source-id", required=True, help="Stable private identifier reused across snapshots"
    )
    i.add_argument("--before", type=float, default=None, help="Exclusive Unix seconds cutoff")
    i.add_argument("--after", type=float, default=0)
    i.add_argument(
        "--after-id", type=int, default=0, help="Resume bounded import from next_after_id"
    )
    i.add_argument("--session")
    i.add_argument("--limit", type=int, default=500)
    i.add_argument("--dry-run", action="store_true")
    i.add_argument("--cohort", choices=["historical", "dogfood"], default="historical")
    i.add_argument(
        "--selection", type=Path, help="Private versioned selection JSON from dataset discovery"
    )
    i.add_argument("--source-revision")
    listing = commands.add_parser("list")
    listing.add_argument("--query", default="")
    listing.add_argument("--status", choices=["pass", "fail", "inconclusive", "not-run"])
    listing.add_argument("--cohort", choices=["historical", "dogfood"])
    listing.add_argument("--split", choices=["development", "held-out", "unassigned"])
    for name in ("show", "report", "export"):
        x = commands.add_parser(name)
        x.add_argument("case_id")
    a = commands.add_parser("annotate")
    a.add_argument("case_id")
    a.add_argument("--text", required=True)
    a.add_argument("--expected")
    a.add_argument("--retracts")
    a.add_argument("--author", choices=["operator", "agent-proposed"], default="operator")
    b = commands.add_parser("baseline")
    b.add_argument("case_id")
    b.add_argument("--logical-path", required=True)
    b.add_argument("--baseline", required=True, help="JSON selected non-secret fields")
    b.add_argument("--current", required=True, help="JSON selected non-secret fields")
    r = commands.add_parser("recipe")
    r.add_argument(
        "--file", required=True, type=Path, help="Recipe JSON; no arbitrary command field"
    )
    r.add_argument(
        "--reviewed", action="store_true", help="Confirm code, revisions and fixture inspection"
    )
    for name in ("run", "compare"):
        x = commands.add_parser(name)
        x.add_argument("recipe_id")
    s = commands.add_parser("serve")
    s.add_argument("--port", type=int, default=8765)
    return p


def doctor(source=None):
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    source = source or home / "state.db"
    info = {
        "schema_version": 1,
        "package_version": version("agent-fix-lab"),
        "python": sys.version.split()[0],
        "hermes_home": str(home),
        "profile": os.environ.get("HERMES_PROFILE", "default"),
        "source": str(source),
        "source_exists": source.is_file(),
        "integration": "profile-local SKILL.md plus isolated CLI",
        "components": {x: version(x) for x in ("triage", "petrichor", "correction-aware-learning")},
    }
    if source.is_file():
        with snapshot(source) as c:
            info["message_columns"] = sorted(validate_schema(c))
            info["sessions"] = c.execute("select count(*) from sessions").fetchone()[0]
            info["messages"] = c.execute("select count(*) from messages").fetchone()[0]
    return info


def main(argv=None):
    args = parser().parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == "doctor":
            result = doctor(args.source)
        else:
            lab = Lab(Store(args.home))
            if args.command == "serve":
                import uvicorn

                from .web import create_app

                uvicorn.run(create_app(lab), host="127.0.0.1", port=args.port)
                return 0
            if args.command == "import-hermes":
                selection = None
                if args.selection:
                    data = json.loads(args.selection.read_text())
                    selection = {x["id"]: x for x in data}
                result = import_hermes(
                    lab.store,
                    args.source,
                    source_id=args.source_id,
                    before=args.before if args.before is not None else time.time(),
                    after=args.after,
                    after_id=args.after_id,
                    session=args.session,
                    limit=args.limit,
                    dry_run=args.dry_run,
                    cohort=args.cohort,
                    selection=selection,
                    source_revision=args.source_revision,
                )
            elif args.command == "list":
                result = lab.list_cases(args.query, args.status, args.cohort, args.split)
            elif args.command == "show":
                result = lab.detail(args.case_id)
            elif args.command in ("export", "report"):
                result = lab.export(args.case_id)
            elif args.command == "annotate":
                result = lab.annotate(
                    args.case_id, args.text, args.expected, args.author, args.retracts
                )
            elif args.command == "baseline":
                result = lab.baseline(
                    args.case_id,
                    args.logical_path,
                    json.loads(args.baseline),
                    json.loads(args.current),
                )
            elif args.command == "recipe":
                result = lab.add_recipe(json.loads(args.file.read_text()), args.reviewed)
            elif args.command == "run":
                result = lab.run(args.recipe_id)
            elif args.command == "compare":
                result = lab.comparison(args.recipe_id)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        if args.command == "run":
            return 0 if result["comparison"]["status"] == "pass" else 2
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
