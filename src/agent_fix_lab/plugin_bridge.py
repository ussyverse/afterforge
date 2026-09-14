"""JSON subprocess bridge to existing services; not imported by plugin registration."""

import json
import os
import signal
import sys
from pathlib import Path

from .corrections import review
from .service import Lab
from .store import Store


def dispatch(home, operation, args):
    lab = Lab(Store(home))
    if operation == "scan":
        return lab.scan(
            Path(args["source"]),
            source_id=args.get("source_id") or os.environ.get("AFTERFORGE_SOURCE_ID"),
            before=args.get("before"),
            session=args.get("session_id"),
            after_id=args.get("after_id"),
            correction_cursor=args.get("correction_cursor"),
            limit=args["limit"],
            cohort="dogfood",
        )
    if operation == "list_cases":
        offset = args.get("offset", 0)
        limit = args.get("limit", 10)
        rows = lab.list_cases(args.get("query", ""), args.get("status"), offset=offset, limit=limit)
        return {
            "cases": rows,
            "next_offset": offset + limit if len(rows) == limit else None,
        }
    if operation == "review_queue":
        from .corrections import candidates

        return candidates(
            lab.store,
            args.get("status", "pending"),
            offset=args.get("offset", 0),
            limit=args.get("limit", 10),
            review_offset=args.get("review_offset", 0),
        )
    if operation == "review_correction":
        return review(
            lab.store,
            args["candidate_id"],
            args["decision"],
            args["note"],
            reviewer=args.get("reviewer", "agent"),
            retracts=args.get("retracts"),
        )
    if operation == "draft_regression":
        return lab.draft_regression(**args)
    if operation == "authorize_draft":
        return lab.authorize_draft(
            args["draft_id"],
            args["approve_digest"],
            reviewed=args.get("reviewed", False),
            declared_inputs=args.get("declared_inputs", False),
        )
    if operation == "guided_case":
        return lab.guided(args["case_id"])
    if operation == "synthetic_demo":
        return lab.synthetic_demo()
    if operation == "retained_plan":
        from .current_check import retained_plan

        return retained_plan(
            lab, args["recipe_id"], args["target_revision"], args.get("reviewed_data_changes")
        )
    if operation == "retained_check":
        from .current_check import retained_check

        return retained_check(
            lab, args["plan_id"], args["approve_digest"], reviewed=args.get("reviewed", False)
        )
    if operation == "verify_current":
        from .current_check import verify

        return verify(lab, args["recipe_id"], args["approve_digest"])
    if operation == "current_check_plan":
        from .models import digest

        recipe = lab.store.get("recipe", args["recipe_id"])
        return {"recipe": recipe, "recipe_digest": digest(recipe), "status": "not-run"}
    if operation == "policy_origin":
        from .models import digest

        identifier = args["case_id"]
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 128:
            raise ValueError("Bounded incident ID required")
        case = lab.store.get("case", identifier)
        return {"case_id": identifier, "case_digest": digest(case)}
    if operation == "inspect_case":
        return lab.detail(args["case_id"], args.get("offset", 0), args.get("limit", 100))
    if operation == "review_case":
        if args.get("candidate_id"):
            return review(
                lab.store,
                args["candidate_id"],
                args.get("decision", "accepted"),
                args["text"],
                reviewer="agent",
                retracts=args.get("retracts"),
            )
        return lab.annotate(
            args["case_id"],
            args["text"],
            args.get("expected"),
            author="agent-proposed",
            retracts=args.get("retracts"),
        )
    if operation in ("build_regression", "register_regression"):
        if args.get("reviewed") is not True:
            raise ValueError("Explicit inspected recipe review is required")
        file = Path(args["recipe_file"]).expanduser().resolve(strict=True)
        if file.stat().st_size > 65536:
            raise ValueError("Recipe file too large")
        return lab.add_recipe(json.loads(file.read_text()), reviewed=True)
    if operation == "verify_regression":
        return lab.run(args["recipe_id"])
    if operation == "report":
        return lab.export(args["case_id"])
    raise ValueError("Unknown backend operation")


def main():
    def stop(*_):
        raise TimeoutError("Backend cancelled")

    signal.signal(signal.SIGTERM, stop)
    request = {}
    try:
        request = json.loads(sys.stdin.buffer.read(65537))
        result = {
            "success": True,
            "data": dispatch(request["home"], request["operation"], request["args"]),
        }
        encoded = json.dumps(result)
        if len(encoded.encode()) > 60000:
            result = {
                "success": False,
                "error": {
                    "code": "result_limit",
                    "message": "Evidence retained locally; narrow the query or use standalone CLI",
                },
                "status": "inconclusive",
            }
    except Exception as exc:
        hints = {
            "scan": "Check source schema 26 and explicit source_id or AFTERFORGE_SOURCE_ID mapping; retry the bounded page",
            "draft_regression": "Supply case, repository, both commits, module/function, explicit examples and expected failure; inspect local code",
            "authorize_draft": "Inspect exact draft; supply approve_digest, reviewed=true and declared_inputs=true",
            "retained_plan": "Supply a reviewed recipe and explicit target commit; declare intentional data/config changes by path",
            "retained_check": "Inspect exact target plan; supply plan_id, approve_digest and reviewed=true",
            "review_correction": "Supply candidate ID, accepted/rejected/retracted decision, nonempty note and valid same-candidate retraction target",
        }
        result = {
            "success": False,
            "error": {
                "code": type(exc).__name__,
                "message": hints.get(
                    request.get("operation") if isinstance(request, dict) else None,
                    "Backend operation failed; inspect local recipe, source schema or identifiers",
                ),
            },
            "status": "inconclusive",
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
