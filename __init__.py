"""Native Hermes entry point; imports only standard-library adapter code."""

from pathlib import Path


def register(ctx):
    from .hermes_plugin.commands import configure, slash
    from .hermes_plugin.runtime import Runtime
    from .hermes_plugin.schemas import SCHEMAS

    runtime = Runtime(ctx, Path(__file__).parent)
    for name, schema in SCHEMAS.items():

        def handler(args, _name=name, **kwargs):
            return runtime.handle(_name, args, **kwargs)

        ctx.register_tool(name=name, toolset="agent-fix-lab", schema=schema, handler=handler)
    ctx.register_hook("post_tool_call", runtime.capture.post_tool_call)
    ctx.register_hook("pre_verify", runtime.pre_verify)
    ctx.register_hook("on_session_end", runtime.capture.on_session_end)
    ctx.register_command(
        "fixlab",
        lambda raw, **kwargs: slash(runtime, raw),
        description="Inspect and maintain reviewed regression evidence",
        args_hint="status | scan | failures | review | help",
    )
    ctx.register_cli_command(
        name="fixlab",
        help="Agent Fix Lab runtime and evidence",
        setup_fn=configure,
        handler_fn=runtime.command,
    )
    ctx.register_skill(
        "regression-workflow", Path(__file__).parent / "skills/regression-workflow/SKILL.md"
    )
