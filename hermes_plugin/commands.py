"""Terminal and gateway-compatible slash commands."""

import json
import shlex


def configure(parser, **kwargs):
    subs = parser.add_subparsers(dest="fixlab_action", required=True)
    for name in ("setup", "doctor", "scan"):
        subs.add_parser(name)
    for name in ("current-check-plan", "verify-current"):
        check = subs.add_parser(name)
        check.add_argument("recipe_id")
        if name == "verify-current":
            check.add_argument("--approve-digest", required=True)
    subs.add_parser("demo")
    queue = subs.add_parser("review")
    queue.add_argument("--offset", type=int, default=0)
    queue.add_argument("--limit", type=int, default=10)
    plan = subs.add_parser("retained-plan")
    plan.add_argument("recipe_id")
    plan.add_argument("target_revision")
    run = subs.add_parser("retained-check")
    run.add_argument("plan_id")
    run.add_argument("--approve-digest", required=True)
    run.add_argument("--reviewed", action="store_true")
    recipe = subs.add_parser("review-recipe")
    recipe.add_argument("recipe_id")
    recipe.add_argument("--approve-digest", required=True)
    policy = subs.add_parser("policy")
    policy.add_argument("operation", choices=["propose", "status", "activate", "rollback"])
    policy.add_argument("--scope")
    policy.add_argument("--case-id")
    policy.add_argument("--approve-digest")
    policy.add_argument("--generation", type=int, default=0)
    serve = subs.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    export = subs.add_parser("export")
    export.add_argument("case_id")
    remove = subs.add_parser("uninstall-runtime")
    remove.add_argument("--confirm", action="store_true")


def slash(runtime, raw, **kwargs):
    try:
        words = shlex.split(raw)
        action = words[0] if words else "help"
        if action == "review":
            if len(words) == 1:
                return json.dumps(runtime.backend("review_queue", {"limit": 10}))
            if words[1] == "page" and len(words) == 3:
                return json.dumps(
                    runtime.backend("review_queue", {"offset": int(words[2]), "limit": 10})
                )
            if words[1] in ("accept", "reject", "retract") and len(words) >= 4:
                decisions = {"accept": "accepted", "reject": "rejected", "retract": "retracted"}
                payload = {
                    "candidate_id": words[2],
                    "decision": decisions[words[1]],
                    "reviewer": "operator",
                    "note": " ".join(words[3:]),
                }
                if words[1] == "retract":
                    if len(words) < 5:
                        raise ValueError("Review ID and note required")
                    payload.update(retracts=words[3], note=" ".join(words[4:]))
                return json.dumps(runtime.backend("review_correction", payload))
            raise ValueError(
                "Use review [page OFFSET | accept/reject ID NOTE | retract ID REVIEW_ID NOTE]"
            )
        if len(words) > 1:
            return json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "arguments",
                        "message": "Use model-callable tools for case-specific review",
                    },
                }
            )
        mapping = {
            "status": ("status", {}),
            "scan": ("scan", {}),
            "failures": ("list_cases", {"status": "fail"}),
        }
        if action in mapping:
            name, args = mapping[action]
            return runtime.handle("fixlab_" + name, args)
        return json.dumps(
            {
                "success": True,
                "data": {
                    "help": "/fixlab status | scan | failures | review | help",
                    "review": "Inspect a case with fixlab_inspect_case, then use fixlab_review_case. Pending candidates are not authenticated human corrections.",
                    "setup": "hermes fixlab setup",
                },
            }
        )
    except Exception:
        return json.dumps(
            {"success": False, "error": {"code": "command", "message": "Invalid command arguments"}}
        )
