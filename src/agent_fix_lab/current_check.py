"""Reviewed committed-checkout checks using the existing isolated recipe runner."""

import time
import uuid

from .models import Recipe, digest
from .runner import execute, git, resolve_recipe


def retained_plan(lab, recipe_id, target_revision, reviewed_data_changes=None):
    """Freeze a NEW explicit target without changing the historical recipe/receipts."""
    original = lab.store.get("recipe", recipe_id)
    if not original.get("reviewed"):
        raise ValueError("A reviewed source recipe is required")
    if original.get("schema_version") != 2 or original.get("input_contract") != "declared-v1":
        raise ValueError("Retained checks require a newly reviewed declared-v1 input contract")
    if not target_revision or target_revision.startswith("-"):
        raise ValueError("Explicit target commit required")
    target = (
        git(original["repository"], "rev-parse", "--verify", f"{target_revision}^{{commit}}")
        .decode()
        .strip()
    )
    recipe = resolve_recipe(
        Recipe(
            **{
                **original,
                "id": uuid.uuid4().hex,
                "corrected_revision": target,
                "reviewed_data_changes": {
                    **original.get("reviewed_data_changes", {}),
                    **(reviewed_data_changes or {}),
                },
            }
        )
    ).model_dump()
    plan = {
        "id": uuid.uuid4().hex,
        "schema_version": 2,
        "source_recipe_id": recipe_id,
        "source_recipe_digest": digest(original),
        "recipe": recipe,
        "target_revision": target,
        "status": "not-run",
        "mode": "committed-archive",
        "live_environment_verified": False,
        "review_required": "Inspect the explicit target commit and unchanged frozen assertion/input contract",
    }
    lab.store.put("retained-plan", plan)
    return {**plan, "plan_digest": digest(plan)}


def retained_check(lab, plan_id, approved_digest, *, reviewed=False):
    plan = lab.store.get("retained-plan", plan_id)
    if not reviewed or digest(plan) != approved_digest:
        raise ValueError("Explicit reviewed target plan digest required")
    original = lab.store.get("recipe", plan["source_recipe_id"])
    if digest(original) != plan["source_recipe_digest"]:
        raise ValueError("Source recipe changed")
    recipe = resolve_recipe(Recipe(**plan["recipe"]))
    lab.store.put("recipe", recipe)
    result = execute(recipe, "corrected")
    lab.store.put("result", result)
    receipt = {
        "id": uuid.uuid4().hex,
        "schema_version": 2,
        "plan_id": plan_id,
        "plan_digest": approved_digest,
        "recipe_id": recipe.id,
        "recipe_digest": digest(recipe.model_dump()),
        "source_recipe_id": plan["source_recipe_id"],
        "result_id": result.id,
        "revision": recipe.corrected_revision,
        "status": "inconclusive"
        if result.input_unknowns or result.frozen_input_digest is None
        else result.status,
        "created_at": time.time(),
        "scope": "reviewed-assertion-on-committed-archive",
        "mode": "committed-archive",
        "live_environment_verified": False,
        "promotion_authorized": False,
    }
    lab.store.put("current-check", receipt)
    return receipt


def checkpoint(recipe):
    """Conservative endpoint check, not filesystem locking or an environment attestation."""
    head = git(recipe.repository, "rev-parse", "HEAD").decode().strip()
    dirty = bool(
        git(recipe.repository, "status", "--porcelain", "--untracked-files=all", "--ignored")
    )
    return {"head": head, "clean": not dirty}


def verify(lab, recipe_id, approved_digest):
    stored = lab.store.get("recipe", recipe_id)
    if approved_digest != digest(stored) or stored.get("reviewed") is not True:
        raise ValueError("Explicit approval of the exact reviewed recipe digest required")
    recipe = resolve_recipe(Recipe(**stored))
    before = checkpoint(recipe)
    if not before["clean"] or before["head"] != recipe.corrected_revision:
        raise ValueError("A clean checkout at the reviewed corrected commit is required")
    authorization = {
        "id": uuid.uuid4().hex,
        "recipe_id": recipe_id,
        "recipe_digest": approved_digest,
        "created_at": time.time(),
        "purpose": "committed-current-check-only",
        "authority": "local-caller-declared",
        "before": before,
    }
    lab.store.put("current-check-authorization", authorization)
    result = execute(recipe, "corrected").model_dump()
    lab.store.put("result", result)
    try:
        after = checkpoint(recipe)
        unchanged = (
            before == after and digest(lab.store.get("recipe", recipe_id)) == approved_digest
        )
        resolve_recipe(recipe)  # Recheck external assertion bytes after execution.
    except (ValueError, KeyError, OSError):
        after, unchanged = None, False
    receipt = {
        "id": uuid.uuid4().hex,
        "schema_version": 1,
        "recipe_id": recipe_id,
        "recipe_digest": approved_digest,
        "authorization_id": authorization["id"],
        "result_id": result["id"],
        "revision": recipe.corrected_revision,
        "created_at": time.time(),
        "before": before,
        "after": after,
        "status": result["status"] if unchanged else "inconclusive",
        "observed_status": result["status"],
        "checkout_unchanged_at_endpoints": unchanged,
        "scope": "reviewed-assertion-on-committed-archive",
        "live_environment_verified": False,
        "promotion_authorized": False,
    }
    lab.store.put("current-check", receipt)
    return receipt
