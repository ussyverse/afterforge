"""JSON subprocess bridge to existing services; not imported by plugin registration."""

import json
import signal
import sys
import time
from pathlib import Path

from .corrections import review
from .history import import_hermes
from .service import Lab
from .store import Store


def dispatch(home, operation, args):
    lab = Lab(Store(home))
    if operation == "scan":
        return import_hermes(
            lab.store,
            Path(args["source"]),
            source_id="native-hermes",
            before=time.time(),
            session=args.get("session_id"),
            after_id=args.get("after_id", 0),
            limit=args["limit"],
            cohort="dogfood",
        )
    if operation == "list_cases":
        rows = lab.list_cases(args.get("query", ""), args.get("status"))
        offset = args.get("offset", 0)
        limit = args.get("limit", 10)
        return {
            "cases": rows[offset : offset + limit],
            "total": len(rows),
            "next_offset": offset + limit if offset + limit < len(rows) else None,
        }
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
        return lab.detail(args["case_id"])
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
    if operation == "build_regression":
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
        result = {
            "success": False,
            "error": {
                "code": type(exc).__name__,
                "message": "Backend operation failed; inspect local recipe, source schema or identifiers",
            },
            "status": "inconclusive",
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
