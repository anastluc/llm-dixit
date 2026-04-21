from __future__ import annotations
"""
Collection management routes.

GET  /api/collections                          — list all collections
GET  /api/collections/{name}                   — collection metadata + card list
DELETE /api/collections/{name}                 — delete a collection from Storage + Firestore
POST /api/collections/{name}/upload            — upload images via multipart form

GET  /api/collections/{name}/cards/{filename}/stats  — per-card game stats
"""

import glob
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

GAME_LOGS_DIR = os.getenv("GAME_LOGS_DIR", "game_logs")
DATA_DIR = os.getenv("DATA_DIR", "data")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _local_collections() -> list[dict]:
    """Discover local image directories under DATA_DIR."""
    results = []
    try:
        for entry in sorted(Path(DATA_DIR).iterdir()):
            if not entry.is_dir():
                continue
            images = [
                f for f in entry.iterdir()
                if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
            ]
            if not images:
                continue
            cards = [
                {"filename": f.name, "url": f"/api/images/{entry.name}/{f.name}"}
                for f in sorted(images)
            ]
            results.append({
                "name": entry.name,
                "display_name": entry.name,
                "source": "local",
                "image_count": len(images),
                "cards": cards,
            })
    except Exception as exc:
        logger.warning("Could not scan local collections: %s", exc)
    return results


def _all_game_logs() -> list[dict]:
    """Load all game logs (Firestore preferred, local fallback)."""
    from core.firebase_store import list_games as fb_list, is_available as fb_ok
    if fb_ok():
        docs = fb_list()
        if docs:
            return docs
    # Local fallback
    logs = []
    for path in glob.glob(os.path.join(GAME_LOGS_DIR, "dixit_game_log_*.json")):
        try:
            with open(path) as f:
                logs.append(json.load(f))
        except Exception:
            pass
    return logs


def _card_key(image_path: str) -> str:
    """Normalise an image_path (local path or URL) to just the filename."""
    return Path(image_path).name


def _compute_card_stats(collection_name: str, filename: str, logs: list[dict]) -> dict:
    """Compute per-card statistics across all game logs."""
    appearances_storyteller = []
    appearances_decoy = []

    for log in logs:
        cfg = log.get("game_configuration", {})
        game_params = cfg.get("game_parameters", cfg)
        players_cfg = cfg.get("players", game_params.get("players", []))
        model_by_name = {p.get("name", ""): p.get("model", "") for p in players_cfg}

        # Only consider games that used this collection
        img_dir = cfg.get("image_directory", game_params.get("image_directory", ""))
        col_from_dir = Path(img_dir).name if img_dir else ""
        # Accept if the directory name matches OR the card URL contains the collection name
        # (Firebase URL contains /collections/{name}/)
        if col_from_dir != collection_name and collection_name not in img_dir:
            # Try to infer from first card in rounds
            first_round = (log.get("rounds") or [{}])[0]
            first_card_path = first_round.get("storyteller_card", "")
            if collection_name not in first_card_path and col_from_dir != collection_name:
                continue

        game_id = log.get("game_id", "")

        for rnd in log.get("rounds", []):
            storyteller = rnd.get("storyteller", "")
            storyteller_card = _card_key(rnd.get("storyteller_card", ""))
            clue = rnd.get("clue", "")

            # All played cards this round
            played = {name: _card_key(info.get("selected_card", ""))
                      for name, info in rnd.get("played_cards", {}).items()}
            played[storyteller] = storyteller_card

            if storyteller_card != filename and filename not in played.values():
                continue

            votes_raw = rnd.get("votes", {})
            votes = {voter: _card_key(info.get("selected_card", ""))
                     for voter, info in votes_raw.items()}
            # storyteller_votes is stored as an int (count) in game logs
            sv = rnd.get("storyteller_votes", 0)
            votes_for = sv if isinstance(sv, int) else len(sv)
            num_voters = len(votes)

            if storyteller_card == filename:
                # This card was the storyteller's card
                appearances_storyteller.append({
                    "game_id": game_id,
                    "round": rnd.get("round"),
                    "model": model_by_name.get(storyteller, "unknown"),
                    "clue": clue,
                    "votes_for": votes_for,
                    "num_voters": num_voters,
                    # Dixit "success" = some but not all voted for storyteller
                    "outcome": (
                        "success" if 0 < votes_for < num_voters
                        else "fail"
                    ) if num_voters > 0 else "unknown",
                })
            else:
                # Played as a decoy by another player
                was_voted = filename in votes.values()
                appearances_decoy.append({
                    "game_id": game_id,
                    "round": rnd.get("round"),
                    "storyteller_clue": clue,
                    "was_voted_for": was_voted,
                })

    total = len(appearances_storyteller) + len(appearances_decoy)
    successes = sum(1 for a in appearances_storyteller if a["outcome"] == "success")
    storyteller_count = len(appearances_storyteller)
    success_rate = round(successes / storyteller_count, 2) if storyteller_count else None

    return {
        "filename": filename,
        "collection": collection_name,
        "total_appearances": total,
        "as_storyteller": {
            "count": storyteller_count,
            "success_rate": success_rate,
            "rounds": appearances_storyteller,
        },
        "as_decoy": {
            "count": len(appearances_decoy),
            "deceived_count": sum(1 for a in appearances_decoy if a["was_voted_for"]),
            "rounds": appearances_decoy,
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/collections")
async def list_collections():
    """List all available image collections (local dirs + Firebase Storage)."""
    from core.firebase_storage import list_collections as fb_list, is_available as storage_ok

    collections = {}

    # Local first
    for col in _local_collections():
        collections[col["name"]] = col

    # Firebase (overrides local entry if same name, adding source=firebase)
    if storage_ok():
        for col in fb_list():
            name = col.get("name", "")
            col["source"] = "firebase"
            collections[name] = col

    return list(collections.values())


@router.get("/collections/{name}")
async def get_collection(name: str):
    """Return metadata + card list for a collection."""
    from core.firebase_storage import get_collection as fb_get, is_available as storage_ok

    if storage_ok():
        meta = fb_get(name)
        if meta:
            meta["source"] = "firebase"
            return meta

    # Local fallback
    local_path = os.path.join(DATA_DIR, name)
    if os.path.isdir(local_path):
        images = sorted(
            f for f in Path(local_path).iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        return {
            "name": name,
            "display_name": name,
            "source": "local",
            "image_count": len(images),
            "cards": [
                {"filename": f.name, "url": f"/api/images/{name}/{f.name}"}
                for f in images
            ],
        }

    raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")


@router.delete("/collections/{name}")
async def delete_collection(name: str):
    from core.firebase_storage import delete_collection as fb_delete, is_available as storage_ok
    if not storage_ok():
        raise HTTPException(status_code=503, detail="Firebase Storage not configured")
    deleted = fb_delete(name)
    return {"deleted_blobs": deleted, "collection": name}


@router.post("/collections/{name}/upload")
async def upload_collection(
    name: str,
    display_name: str = Form(default=""),
    files: List[UploadFile] = File(...),
):
    """Upload images to a new (or existing) Firebase Storage collection."""
    from core.firebase_storage import _get_bucket, _col, is_available as storage_ok
    import tempfile
    from datetime import datetime

    if not storage_ok():
        raise HTTPException(status_code=503, detail="Firebase Storage not configured")

    bucket = _get_bucket()
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    cards = []

    with tempfile.TemporaryDirectory() as tmp:
        for upload in files:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in image_extensions:
                continue
            tmp_path = os.path.join(tmp, upload.filename)
            content = await upload.read()
            with open(tmp_path, "wb") as f:
                f.write(content)

            blob_path = f"collections/{name}/{upload.filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(tmp_path)
            blob.make_public()
            cards.append({"filename": upload.filename, "url": blob.public_url})

    if not cards:
        raise HTTPException(status_code=400, detail="No valid image files uploaded")

    metadata = {
        "name": name,
        "display_name": display_name or name,
        "image_count": len(cards),
        "created_at": datetime.now().isoformat(),
        "cards": cards,
    }
    col = _col()
    if col:
        col.document(name).set(metadata)

    return metadata


@router.get("/collections/{name}/cards/{filename}/stats")
async def card_stats(name: str, filename: str):
    """Return game statistics for a specific card."""
    logs = _all_game_logs()
    return _compute_card_stats(name, filename, logs)
