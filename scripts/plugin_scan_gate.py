"""Stock-host release verification. Does not replace or configure its scanner.

CI may confirm the already reviewed, exact privacy-document warning only after
this gate. New high/critical findings stop publication and require human review.
"""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    root = args.release
    provenance = json.loads((root / "RELEASE.json").read_text())
    for name, entry in provenance["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == entry["sha256"], name
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert actual == set(provenance["files"]) | {"RELEASE.json"}
    from tools.plugin_guard import scan_plugin

    result = scan_plugin(root, source="ussyverse/agent-fix-lab")
    assert result.verdict != "dangerous", "Stock scanner blocked release"
    reviewed = []
    for finding in result.findings:
        if finding.severity not in ("high", "critical"):
            continue
        assert (finding.pattern_id, finding.file, finding.line) == (
            "context_exfil",
            "docs/privacy.md",
            9,
        ), finding
        assert hashlib.sha256((root / finding.file).read_bytes()).hexdigest() == (
            "bde77e91c873461941ef72b603edba6e195eff3977ecab33e8cf5906d5f83c15"
        ), "Privacy documentation changed; review the warning again"
        reviewed.append(finding.pattern_id)
    print(
        json.dumps(
            {
                "stock_scanner": result.scan_provenance,
                "findings": len(result.findings),
                "reviewed_cautions": reviewed,
                "source_commit": provenance["source_commit"],
                "verified_release_files": len(actual),
            }
        )
    )


if __name__ == "__main__":
    main()
