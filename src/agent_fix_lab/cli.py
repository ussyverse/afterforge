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
    shadow = commands.add_parser("verification-shadow")
    shadow.add_argument("--file", type=Path, required=True)
    shadow.add_argument("--captured-bindings", action="store_true")
    draft = commands.add_parser("intervention-propose")
    draft.add_argument("--file", type=Path, required=True)
    listing_interventions = commands.add_parser("intervention-list")
    listing_interventions.add_argument("--offset", type=int, default=0)
    listing_interventions.add_argument("--limit", type=int, default=10)
    show_intervention = commands.add_parser("intervention-show")
    show_intervention.add_argument("intervention_id")
    evaluate_intervention = commands.add_parser("intervention-evaluate")
    evaluate_intervention.add_argument("intervention_id")
    evaluate_intervention.add_argument("--candidate-digest", required=True)
    evaluate_intervention.add_argument("--reviewed", action="store_true")
    review_intervention = commands.add_parser("intervention-review")
    review_intervention.add_argument("intervention_id")
    review_intervention.add_argument("--evaluation-id", required=True)
    review_intervention.add_argument("--candidate-digest", required=True)
    review_intervention.add_argument(
        "--decision", choices=["accept-evidence", "reject"], required=True
    )
    review_intervention.add_argument("--note", required=True)
    scan = commands.add_parser("correction-scan")
    scan.add_argument("--source", type=Path, required=True)
    scan.add_argument("--source-id", required=True)
    scan.add_argument("--before", type=float, required=True)
    scan.add_argument("--after", type=float, default=0)
    scan.add_argument("--limit", type=int, default=500)
    candidates = commands.add_parser("corrections")
    candidates.add_argument("--status", choices=["pending", "accepted", "rejected"])
    review = commands.add_parser("review-correction")
    review.add_argument("candidate_id")
    review.add_argument("--decision", choices=["accepted", "rejected", "retracted"], required=True)
    review.add_argument("--note", required=True)
    review.add_argument(
        "--reviewer", choices=["operator", "human-declared", "agent"], default="operator"
    )
    review.add_argument("--retracts")
    bundle = commands.add_parser("bundle-export")
    bundle.add_argument("recipe_id")
    bundle.add_argument("--output", type=Path, required=True)
    bundle.add_argument("--problem", required=True)
    bundle.add_argument("--expected", required=True)
    bundle.add_argument("--failure", required=True)
    bundle.add_argument("--file", action="append", dest="files", required=True)
    bundle.add_argument("--approved", action="store_true")
    for name in ("bundle-import", "bundle-validate"):
        sub = commands.add_parser(name)
        sub.add_argument("file", type=Path)
        if name == "bundle-import":
            sub.add_argument("--reviewed", action="store_true")
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
    plan = commands.add_parser("current-check-plan")
    plan.add_argument("recipe_id")
    current = commands.add_parser("verify-current")
    current.add_argument("recipe_id")
    current.add_argument("--approve-digest", required=True)
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
        if args.command == "verification-shadow":
            from .verification import assess

            with args.file.open("rb") as source:
                raw = source.read(262145)
            if len(raw) > 262144:
                raise ValueError("Evidence exceeds 256 KiB")
            if args.captured_bindings:
                from .verification_binding import bind_assess

                result = bind_assess(json.loads(raw))
            else:
                result = assess(json.loads(raw))
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "doctor":
            result = doctor(args.source)
        else:
            lab = Lab(Store(args.home))
            if args.command.startswith("intervention-"):
                from . import interventions

                if args.command == "intervention-propose":
                    with args.file.open("rb") as stream:
                        raw = stream.read(65537)
                    if len(raw) > 65536:
                        raise ValueError("Proposal file too large")
                    result = interventions.propose(lab, json.loads(raw))
                elif args.command == "intervention-list":
                    result = interventions.listing(lab, args.offset, args.limit)
                elif args.command == "intervention-show":
                    result = interventions.inspect(lab, args.intervention_id)
                elif args.command == "intervention-evaluate":
                    result = interventions.evaluate(
                        lab, args.intervention_id, args.candidate_digest, reviewed=args.reviewed
                    )
                else:
                    result = interventions.review(
                        lab,
                        args.intervention_id,
                        args.evaluation_id,
                        args.candidate_digest,
                        args.decision,
                        args.note,
                    )
                print(json.dumps(result, indent=2))
                return (
                    2
                    if args.command == "intervention-evaluate" and result["status"] != "pass"
                    else 0
                )
            if args.command in {
                "correction-scan",
                "corrections",
                "review-correction",
                "bundle-export",
                "bundle-import",
                "bundle-validate",
            }:
                from . import bundles, corrections

                if args.command == "correction-scan":
                    result = corrections.scan(
                        lab.store, args.source, args.source_id, args.before, args.after, args.limit
                    )
                elif args.command == "corrections":
                    result = corrections.candidates(lab.store, args.status)
                elif args.command == "review-correction":
                    result = corrections.review(
                        lab.store,
                        args.candidate_id,
                        args.decision,
                        args.note,
                        args.reviewer,
                        args.retracts,
                    )
                elif args.command == "bundle-export":
                    result = bundles.export_bundle(
                        lab,
                        args.recipe_id,
                        args.output,
                        problem=args.problem,
                        expected=args.expected,
                        failure=args.failure,
                        files=args.files,
                        approved=args.approved,
                    )
                elif args.command == "bundle-import":
                    result = bundles.import_bundle(lab, args.file, args.reviewed)
                else:
                    validated = bundles.validate(args.file)
                    result = {
                        "status": "valid",
                        "case_id": validated["case_id"],
                        "integrity": validated["integrity"],
                        "execution_authorized": False,
                    }
                print(json.dumps(result, indent=2))
                return 0
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
            elif args.command == "current-check-plan":
                from .models import digest

                recipe = lab.store.get("recipe", args.recipe_id)
                result = {"recipe": recipe, "recipe_digest": digest(recipe), "status": "not-run"}
            elif args.command == "verify-current":
                from .current_check import verify

                result = verify(lab, args.recipe_id, args.approve_digest)
            elif args.command == "run":
                result = lab.run(args.recipe_id)
            elif args.command == "compare":
                result = lab.comparison(args.recipe_id)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        if args.command == "verify-current":
            return 0 if result["status"] == "pass" else 2
        if args.command == "run":
            return 0 if result["comparison"]["status"] == "pass" else 2
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
