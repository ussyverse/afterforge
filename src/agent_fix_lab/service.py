"""Application workflow shared by CLI and local UI."""

import hashlib
import time
import uuid
from pathlib import Path

from .adapters import configuration_difference, configuration_snapshot, structural_annotation
from .models import Annotation, Recipe, ReproductionResult, digest
from .runner import compare, execute, resolve_recipe


class Lab:
    def __init__(self, store):
        self.store = store

    def list_cases(self, query="", status=None, cohort=None, split=None):
        result = []
        for case in self.store.all("case"):
            run = self.store.get("run", case["run_id"])
            if status and run["observed_status"] != status:
                continue
            if cohort and case["cohort"] != cohort:
                continue
            if split and case["split"] != split:
                continue
            if query.lower() not in (run["output"] + case["id"]).lower():
                continue
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

    def detail(self, identifier):
        case = self.store.get("case", identifier)
        annotations = [x for x in self.store.all("annotation") if x["case_id"] == identifier]
        retracted = set()
        for item in reversed(annotations):
            if item["id"] not in retracted and item.get("retracts"):
                retracted.add(item["retracts"])
        recipes = [x for x in self.store.all("recipe") if x["case_id"] == identifier]
        results = [
            x for x in self.store.all("result") if x["recipe_id"] in {r["id"] for r in recipes}
        ]
        baselines = [x for x in self.store.all("baseline") if x["case_id"] == identifier]
        return {
            "case": case,
            "observations": self.store.get("run", case["run_id"]),
            "source_observations": [
                x for x in self.store.all("source-observation") if x["case_id"] == identifier
            ],
            "interpretations": annotations,
            "effective_interpretations": [x for x in annotations if x["id"] not in retracted],
            "recipes": recipes,
            "results": results,
            "configuration_difference": configuration_difference(
                baselines[-1]["baseline"] if baselines else None,
                baselines[-1]["current"] if baselines else None,
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
        results = [
            ReproductionResult(**x) for x in self.store.all("result") if x["recipe_id"] == recipe_id
        ]
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
        }
