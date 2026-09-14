"""Application workflow shared by CLI and local UI."""

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from .adapters import configuration_difference, configuration_snapshot, structural_annotation
from .models import Annotation, Recipe, ReproductionResult, digest
from .runner import compare, execute, resolve_recipe


class Lab:
    def __init__(self, store):
        self.store = store

    def scan(self, *args, **kwargs):
        with self.store.workflow_lock("scan"):
            return self._scan(*args, **kwargs)

    def _scan(
        self,
        source,
        source_id,
        *,
        before=None,
        after=0,
        after_id=None,
        session=None,
        limit=100,
        correction_cursor=None,
        dry_run=False,
        cohort="dogfood",
        **options,
    ):
        """One bounded page per independent stream, with immutable resumable receipts.

        source_id is an explicit profile mapping shared by all entrypoints; never a filename.
        """
        from .corrections import scan
        from .history import import_hermes

        if not isinstance(source_id, str) or not source_id.strip():
            # Diagnose unsupported inputs without allocating any source identity.
            from .history import snapshot, validate_schema

            with snapshot(source) as connection:
                validate_schema(connection)
            raise ValueError("Explicit source/profile mapping required")
        scope = digest(
            [
                source_id,
                session,
                after,
                cohort,
                options.get("source_revision"),
                options.get("selection"),
            ]
        )
        with self.store.connect() as c:
            row = c.execute(
                "select body from documents where kind='scan-cursor' "
                "and json_extract(body,'$.scope')=? order by rowid desc limit 1",
                (scope,),
            ).fetchone()
        previous = json.loads(row[0]) if row else {}
        tool_cursor = previous.get("after_id", 0) if after_id is None else after_id
        cursor = correction_cursor or previous.get(
            "correction_cursor", {"timestamp": after, "id": 0}
        )
        cutoff = time.time() if before is None else before
        tools = import_hermes(
            self.store,
            source,
            source_id=source_id,
            before=cutoff,
            after=after,
            after_id=tool_cursor,
            session=session,
            limit=limit,
            dry_run=dry_run,
            cohort=cohort,
            **options,
        )
        corrections = {"status": "not-run", "reason": "dry run"}
        if not dry_run:
            corrections = scan(
                self.store,
                source,
                source_id,
                cutoff,
                cursor["timestamp"],
                limit,
                cursor["id"],
                session,
            )
            self.store.put(
                "scan-cursor",
                {
                    "id": uuid.uuid4().hex,
                    "scope": scope,
                    "source_id": source_id,
                    "after_id": tools["next_after_id"],
                    "correction_cursor": corrections["next_cursor"],
                },
            )
        return {**tools, "corrections": corrections, "source_id": source_id}

    def draft_regression(
        self,
        case_id,
        repository,
        faulty_revision,
        corrected_revision,
        module,
        function,
        examples,
        expected_behavior,
        intended_failure,
        provenance="derived",
        reviewed_data_changes=None,
    ):
        """Generate a concrete deterministic call/assertion reduction, never replay history."""
        case = self.store.get("case", case_id)
        run = self.store.get("run", case["run_id"])
        if provenance not in ("derived", "synthetic"):
            raise ValueError("Drafts are reductions, not historical reconstruction")
        if not re.fullmatch(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", module) or not re.fullmatch(
            r"[A-Za-z_]\w*", function
        ):
            raise ValueError("Expected Python module and function identifiers")
        if not isinstance(examples, list) or not 1 <= len(examples) <= 100:
            raise ValueError("Supply 1..100 explicitly selected examples")
        for example in examples:
            if (
                not isinstance(example, dict)
                or set(example) != {"args", "expected"}
                or not isinstance(example["args"], list)
            ):
                raise ValueError("Each example requires args list and expected JSON value")
        content = json.dumps(examples, ensure_ascii=False, allow_nan=False)
        if len(content.encode("utf-8")) > 65536:
            raise ValueError("Draft inputs exceed 64 KiB")
        identifier = uuid.uuid4().hex
        directory = self.store.root / "drafts" / identifier
        directory.mkdir(parents=True, mode=0o700)
        test = directory / "test_regression.py"
        assertion = (
            "import json\nimport os\nfrom pathlib import Path\nimport pytest\n"
            f"from {module} import {function} as subject\n\n"
            "EXAMPLES = json.loads((Path(os.environ['AFTERFORGE_FROZEN_INPUTS']) / 'examples.json').read_text(encoding='utf-8'))\n"
            "@pytest.mark.parametrize('example', EXAMPLES)\n"
            "def test_reviewed_behavior(example):\n"
            f"    assert subject(*example['args']) == example['expected'], {intended_failure!r}\n"
        )
        test.write_text(assertion, encoding="utf-8")
        os.chmod(test, 0o600)
        recipe = Recipe(
            schema_version=2,
            id=identifier,
            case_id=case_id,
            repository=repository,
            faulty_revision=faulty_revision,
            corrected_revision=corrected_revision,
            test_file=str(test),
            test_sha256=hashlib.sha256(test.read_bytes()).hexdigest(),
            expected_behavior=expected_behavior,
            intended_failure=intended_failure,
            frozen_inputs=[
                {
                    "logical_path": "examples.json",
                    "content": content,
                    "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                }
            ],
            input_contract="unknown",
            reviewed_data_changes=reviewed_data_changes or {},
            provenance=provenance,
        )
        recipe = resolve_recipe(recipe).model_dump()
        proposal = {
            "id": identifier,
            "case_id": case_id,
            "schema_version": 2,
            "recipe": recipe,
            "assertion": assertion,
            "source_refs": [run["source"]],
            "unknowns": [
                "historical implementation and environment",
                "dependency completeness requires user inspection",
            ],
            "reconstruction": False,
            "status": "draft",
            "execution_authorized": False,
            "input_declaration_required": "Deterministic reviewed code; all regression inputs frozen or literal; no ambient file/network/clock/random/environment inputs or hidden mutable globals/fixture side effects.",
        }
        self.store.put("regression-draft", proposal)
        return {**proposal, "draft_digest": digest(proposal)}

    def authorize_draft(self, draft_id, approved_digest, *, reviewed=False, declared_inputs=False):
        with self.store.workflow_lock("authorize-draft"):
            return self._authorize_draft(
                draft_id, approved_digest, reviewed=reviewed, declared_inputs=declared_inputs
            )

    def _authorize_draft(self, draft_id, approved_digest, *, reviewed=False, declared_inputs=False):
        proposal = self.store.get("regression-draft", draft_id)
        if not reviewed or not declared_inputs or digest(proposal) != approved_digest:
            raise ValueError(
                "Exact draft digest, code review and explicit dependency/input declaration required"
            )
        recipe = {**proposal["recipe"], "input_contract": "declared-v1"}
        # Never recompute the reviewed assertion hash when authorizing a draft.
        resolve_recipe(Recipe(**recipe))
        existing = self.store.page("draft-authorization", field="scope", value=draft_id, limit=1)
        if existing:
            return self.store.get("recipe", existing[0]["recipe_id"])
        saved = resolve_recipe(
            Recipe(**{**recipe, "id": uuid.uuid4().hex, "reviewed": True})
        ).model_dump()
        self.store.put_many(
            [
                ("recipe", saved),
                (
                    "draft-authorization",
                    {
                        "id": uuid.uuid4().hex,
                        "scope": draft_id,
                        "recipe_id": saved["id"],
                        "draft_digest": approved_digest,
                        "authority": "operator-declared",
                        "input_contract": "declared-v1",
                    },
                ),
            ]
        )
        return saved

    def guided(self, case_id):
        detail = self.detail(case_id)
        drafts = self.store.page("regression-draft", field="case_id", value=case_id)
        recipes = detail["recipes"]
        latest = self.store.latest("recipe", "case_id", case_id)
        comparison = self.comparison(latest["id"]) if latest else {"status": "not-run"}
        action = (
            "draft"
            if not drafts and not recipes
            else "review draft"
            if not recipes
            else "run regression"
        )
        if comparison["status"] == "pass":
            action = "retain check at an explicit reviewed commit"
        return {
            "detail": detail,
            "drafts": [{**draft, "draft_digest": digest(draft)} for draft in drafts],
            "comparison": comparison,
            "next_action": action,
            "scope": "reviewed regression retention; no autonomous learning or historical reconstruction",
        }

    def synthetic_demo(self):
        """Create only labeled synthetic evidence and a private miniature Git subject."""
        from .models import Case, Run, SourceRecord
        from .runner import git

        identifier = digest(["afterforge-synthetic-demo", uuid.uuid4().hex])
        repo = self.store.root / "demos" / identifier
        repo.mkdir(parents=True, mode=0o700)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        git(repo, "config", "user.name", "Synthetic demo")
        git(repo, "config", "user.email", "demo@example.invalid")
        subject = repo / "implementation.py"
        subject.write_text("def classify(code):\n    return 'pass'\n")
        git(repo, "add", "implementation.py")
        git(repo, "commit", "-qm", "Synthetic faulty subject")
        faulty = git(repo, "rev-parse", "HEAD").decode().strip()
        subject.write_text("def classify(code):\n    return 'pass' if code == 0 else 'fail'\n")
        git(repo, "add", "implementation.py")
        git(repo, "commit", "-qm", "Synthetic corrected subject")
        corrected = git(repo, "rev-parse", "HEAD").decode().strip()
        source = SourceRecord(
            id=identifier,
            source_id="synthetic-demo",
            session_id=identifier,
            message_id=1,
            timestamp_seconds=time.time(),
            payload_digest=digest("synthetic"),
        )
        self.store.put_many(
            [
                (
                    "run",
                    Run(
                        id=identifier,
                        source=source,
                        observed_status="fail",
                        exit_code=3,
                        output="Synthetic example: nonzero process exit was classified as pass",
                    ),
                ),
                (
                    "case",
                    Case(
                        id=identifier,
                        run_id=identifier,
                        incident_group=identifier,
                        provenance="synthetic",
                    ),
                ),
            ]
        )
        return self.draft_regression(
            identifier,
            str(repo),
            faulty,
            corrected,
            "implementation",
            "classify",
            [{"args": [3], "expected": "fail"}, {"args": [0], "expected": "pass"}],
            "Nonzero exits fail; zero exits pass",
            "nonzero must fail",
            provenance="synthetic",
        )

    def list_cases(self, query="", status=None, cohort=None, split=None, offset=0, limit=100):
        if offset < 0 or not 1 <= limit <= 10000:
            raise ValueError("Invalid pagination")
        conditions = [
            "c.kind='case'",
            "r.kind='run'",
            "instr(lower(json_extract(r.body,'$.output') || c.id),lower(?))>0",
        ]
        args = [query]
        for field, value in (
            ("r.observed_status", status),
            ("c.cohort", cohort),
            ("c.split", split),
        ):
            if value:
                alias, key = field.split(".")
                conditions.append(f"json_extract({alias}.body,'$.{key}')=?")
                args.append(value)
        with self.store.connect() as connection:
            rows = connection.execute(
                "select c.body,r.body from documents c join documents r "
                "on r.id=json_extract(c.body,'$.run_id') where "
                + " and ".join(conditions)
                + " order by c.rowid limit ? offset ?",
                [*args, limit, offset],
            ).fetchall()
        result = []
        for case_body, run_body in rows:
            case, run = json.loads(case_body), json.loads(run_body)
            result.append(
                {
                    **case,
                    "status": run["observed_status"],
                    "tool": run["source"]["tool_name"],
                    "summary": run["output"][:180],
                    "unknown": run["unknown"],
                }
            )
        return result

    def detail(self, identifier, offset=0, limit=100):
        from .corrections import candidates

        case = self.store.get("case", identifier)
        annotations = self.store.page(
            "annotation", field="case_id", value=identifier, offset=offset, limit=limit
        )
        recipes = self.store.page(
            "recipe", field="case_id", value=identifier, offset=offset, limit=limit
        )
        results = self.store.related_results(identifier, limit=limit, offset=offset)
        baseline = self.store.latest("baseline", "case_id", identifier)
        return {
            "case": case,
            "observations": self.store.get("run", case["run_id"]),
            "source_observations": self.store.page(
                "source-observation", field="case_id", value=identifier, offset=offset, limit=limit
            ),
            "interpretations": annotations,
            "correction_candidates": candidates(
                self.store, case_id=identifier, offset=offset, limit=limit
            ),
            "pagination": {"offset": offset, "limit": limit, "bounded": True},
            "effective_interpretations": self.store.effective_annotations(
                identifier, offset, limit
            ),
            "recipes": recipes,
            "results": results,
            "configuration_difference": configuration_difference(
                baseline["baseline"] if baseline else None,
                baseline["current"] if baseline else None,
            ),
            "execution_available": bool(recipes),
            "unavailable_reason": None
            if recipes
            else "Create and explicitly review a pytest recipe first",
        }

    def annotate(self, identifier, text, expected=None, author="operator", retracts=None):
        self.store.get("case", identifier)
        if author not in ("operator", "agent-proposed"):
            raise ValueError(
                "Historical-user attribution requires original authenticated source; unavailable here"
            )
        if retracts:
            old = self.store.get("annotation", retracts)
            if old["case_id"] != identifier:
                raise ValueError("Cannot retract another case annotation")
            if author == "agent-proposed" and old["author_kind"] != "agent-proposed":
                raise ValueError("Agent cannot retract operator interpretation")
        annotation = Annotation(
            id=uuid.uuid4().hex,
            case_id=identifier,
            timestamp_seconds=time.time(),
            author_kind=author,
            text=text,
            expected_behavior=expected,
            retracts=retracts,
        )
        self.store.put("annotation", annotation)
        structural_annotation(self.store.root, annotation)
        return annotation.model_dump()

    def add_recipe(self, values, reviewed=False):
        values = {**values, "id": uuid.uuid4().hex, "reviewed": reviewed}
        self.store.get("case", values["case_id"])
        test = Path(values["test_file"]).expanduser().resolve(strict=True)
        values["test_sha256"] = hashlib.sha256(test.read_bytes()).hexdigest()
        recipe = resolve_recipe(Recipe(**values))
        self.store.put("recipe", recipe)
        return recipe.model_dump()

    def run(self, recipe_id):
        recipe = Recipe(**self.store.get("recipe", recipe_id))
        results = []
        for variant in ("faulty", "corrected"):
            result = execute(recipe, variant)
            self.store.put("result", result)
            results.append(result)
        comparison = compare(recipe, *results)
        self.store.put("comparison", {"id": uuid.uuid4().hex, **comparison.model_dump()})
        return {"comparison": comparison.model_dump(), "results": [x.model_dump() for x in results]}

    def comparison(self, recipe_id):
        recipe = Recipe(**self.store.get("recipe", recipe_id))
        results = [ReproductionResult(**x) for x in self.store.latest_variants(recipe_id)]
        variants = {r.variant: r for r in results}
        return compare(recipe, variants.get("faulty"), variants.get("corrected")).model_dump()

    def baseline(self, case_id, logical_path, baseline, current):
        self.store.get("case", case_id)
        old = configuration_snapshot(self.store.root, logical_path, baseline)
        new = configuration_snapshot(self.store.root, logical_path, current)
        record = {
            "id": uuid.uuid4().hex,
            "case_id": case_id,
            "schema_version": 1,
            "baseline": old,
            "current": new,
            "note": "Operator-selected fields; not proof of historical configuration",
        }
        self.store.put("baseline", record)
        return configuration_difference(old, new)

    def export(self, case_id):
        # Allowlist projection, not regex redaction. Arbitrary text/IDs never exported.
        detail = self.detail(case_id)
        run = detail["observations"]
        return {
            "schema_version": 1,
            "format": "agent-fix-lab.public-summary.v1",
            "case_alias": digest(case_id)[:12],
            "provenance": detail["case"]["provenance"],
            "observed_status": run["observed_status"],
            "exit_code": run["exit_code"],
            "evidence_missing_count": len(run["unknown"]),
            "annotation_count": len(detail["interpretations"]),
            "correction_candidate_count": len(detail["correction_candidates"]),
            "recipe_count": len(detail["recipes"]),
            "results": [
                {
                    "status": x["status"],
                    "tests": x["tests"],
                    "failures": x["failures"],
                    "errors": x["errors"],
                    "skipped": x["skipped"],
                }
                for x in detail["results"]
            ],
            "excluded": [
                "source_records",
                "paths",
                "output",
                "configuration",
                "annotation_text",
                "commands",
                "identifiers",
            ],
            "shadow_only": True,
            "counts_scope": "bounded detail page; not whole-store totals",
        }
