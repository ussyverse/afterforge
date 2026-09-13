"""Terminal and gateway-compatible slash commands."""

import json
import shlex


def configure(parser, **kwargs):
    subs = parser.add_subparsers(dest="fixlab_action", required=True)
    for name in ("setup", "doctor", "scan"):
        subs.add_parser(name)
    policy = subs.add_parser("policy")
    policy.add_argument("operation", choices=["propose", "status", "activate", "rollback"])
    policy.add_argument("--scope")
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
