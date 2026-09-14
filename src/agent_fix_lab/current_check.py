"""Reviewed committed-checkout checks using the existing isolated recipe runner."""

import time
import uuid

from .models import Recipe, digest
from .runner import execute, git, resolve_recipe


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
