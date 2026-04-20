import os
import json
import logging
import threading
from io import BytesIO
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import List
from fastapi.responses import StreamingResponse
from backend.database import (
    create_session, update_session, get_session, save_player_profile,
    get_results, list_sessions, append_agent_log_event, get_agent_log_live,
)
from backend.agents.orchestrator import Orchestrator
from backend.utils.video_processor import extract_clip, get_clip_duration
from backend.config import UPLOADS_DIR, HIGHLIGHTS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES  = 2 * 1024 * 1024 * 1024
_scout_semaphore  = threading.Semaphore(2)


def process_vod(session_id: int, clip_path: str, context: dict):
    try:
        update_session(session_id, status="analysing")
        acquired = _scout_semaphore.acquire(timeout=300)
        if not acquired:
            update_session(session_id, status="failed",
                           error_message="Server busy — retry in a minute.")
            return
        try:
            _run_scouting(session_id, clip_path, context)
        finally:
            _scout_semaphore.release()
    except Exception as e:
        logger.error(f"process_vod outer error session {session_id}: {e}", exc_info=True)
        update_session(session_id, status="failed", error_message=f"{type(e).__name__}: {e}")
    finally:
        if os.path.exists(clip_path):
            try:
                os.remove(clip_path)
            except Exception as ex:
                logger.warning(f"Cleanup failed {clip_path}: {ex}")


def _run_scouting(session_id: int, clip_path: str, context: dict):
    try:
        def log_callback(log: list):
            if log:
                append_agent_log_event(session_id, log[-1])

        orchestrator = Orchestrator()
        result = orchestrator.run(str(clip_path), context, log_callback=log_callback)

        if not result:
            update_session(session_id, status="failed",
                           error_message="Orchestrator returned no result")
            return

        agent_log = result.pop("_agent_log", [])
        update_session(session_id,
                       full_result=json.dumps(result),
                       status="complete")

        # Extract highlight clips around the top timestamps
        clip_duration = get_clip_duration(str(clip_path))
        highlight_clips = []
        for i, ts in enumerate(result.get("highlights", [])[:5]):
            out_name = f"s{session_id}_h{i}.mp4"
            out_path = HIGHLIGHTS_DIR / out_name
            try:
                start = max(0.0, ts - 5)
                end   = min(ts + 10, clip_duration) if clip_duration > 0 else ts + 10
                if end > start:
                    extract_clip(str(clip_path), start, end, str(out_path))
                    highlight_clips.append(f"/highlights/{out_name}")
            except Exception as e:
                logger.warning(f"Highlight extraction failed at {ts}s: {e}")

        result["highlight_clips"] = highlight_clips
        update_session(session_id, full_result=json.dumps(result))

        save_player_profile(session_id, {
            "player_handle":   result.get("player_handle"),
            "archetype":       result.get("archetype"),
            "style_vector":    result.get("style_vector", {}),
            "pro_match_handle": (result.get("pro_match") or {}).get("handle"),
            "pro_match_team":  (result.get("pro_match") or {}).get("team"),
            "similarity_score": result.get("similarity_score"),
            "market_value":    result.get("market_value"),
            "risk_tier":       result.get("risk_tier"),
            "summary":         result.get("twin_narrative", ""),
        })

        logger.info(f"Session {session_id} completed — {result.get('player_handle')}")

    except Exception as e:
        logger.error(f"Scouting session {session_id} failed: {e}", exc_info=True)
        update_session(session_id, status="failed", error_message=f"{type(e).__name__}: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/scout")
async def scout(
    background_tasks: BackgroundTasks,
    clip: UploadFile = File(...),
    player_handle: str = Form(...),
    game: str = Form("r6siege"),
    team: str = Form(""),
):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    HIGHLIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    content = await clip.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 2 GB)")

    session_id = create_session(clip.filename, player_handle, game, team)
    clip_path  = UPLOADS_DIR / f"{session_id}_{clip.filename}"
    with open(clip_path, "wb") as f:
        f.write(content)

    context = {
        "player_handle": player_handle,
        "game":          game,
        "team":          team,
    }
    background_tasks.add_task(process_vod, session_id, clip_path, context)
    return {"session_id": session_id, "status": "uploading"}


@router.post("/scout/multi")
async def scout_multi(
    background_tasks: BackgroundTasks,
    clips: List[UploadFile] = File(...),
    player_handle: str = Form(...),
    game: str = Form("r6siege"),
    team: str = Form(""),
):
    if len(clips) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 clips for multi-clip profiling")
    if len(clips) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 clips per session")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    HIGHLIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = create_session(
        f"multi_{len(clips)}_clips", player_handle, game, team
    )

    clip_paths = []
    for i, clip in enumerate(clips):
        content = await clip.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Clip {i+1} too large (max 2 GB)")
        path = UPLOADS_DIR / f"{session_id}_c{i}_{clip.filename}"
        with open(path, "wb") as f:
            f.write(content)
        clip_paths.append(str(path))

    context = {"player_handle": player_handle, "game": game, "team": team}
    background_tasks.add_task(process_multi_vod, session_id, clip_paths, context)
    return {"session_id": session_id, "status": "uploading", "clips": len(clips)}


def process_multi_vod(session_id: int, clip_paths: list[str], context: dict):
    try:
        update_session(session_id, status="analysing")
        acquired = _scout_semaphore.acquire(timeout=600)
        if not acquired:
            update_session(session_id, status="failed",
                           error_message="Server busy — retry in a minute.")
            return
        try:
            _run_multi_scouting(session_id, clip_paths, context)
        finally:
            _scout_semaphore.release()
    except Exception as e:
        logger.error(f"process_multi_vod outer error {session_id}: {e}", exc_info=True)
        update_session(session_id, status="failed", error_message=f"{type(e).__name__}: {e}")
    finally:
        for path in clip_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as ex:
                    logger.warning(f"Cleanup failed {path}: {ex}")


def _run_multi_scouting(session_id: int, clip_paths: list[str], context: dict):
    try:
        def log_callback(log: list):
            if log:
                append_agent_log_event(session_id, log[-1])

        orchestrator = Orchestrator()
        result = orchestrator.run_multi(clip_paths, context, log_callback=log_callback)

        if not result:
            update_session(session_id, status="failed",
                           error_message="Orchestrator returned no result")
            return

        result.pop("_agent_log", [])
        update_session(session_id, full_result=json.dumps(result), status="complete")

        save_player_profile(session_id, {
            "player_handle":    result.get("player_handle"),
            "archetype":        result.get("archetype"),
            "style_vector":     result.get("style_vector", {}),
            "pro_match_handle": (result.get("pro_match") or {}).get("handle"),
            "pro_match_team":   (result.get("pro_match") or {}).get("team"),
            "similarity_score": result.get("similarity_score"),
            "market_value":     result.get("market_value"),
            "risk_tier":        result.get("risk_tier"),
            "summary":          result.get("twin_narrative", ""),
        })
        logger.info(f"Multi-session {session_id} completed — {result.get('player_handle')}")

    except Exception as e:
        logger.error(f"Multi scouting session {session_id} failed: {e}", exc_info=True)
        update_session(session_id, status="failed", error_message=f"{type(e).__name__}: {e}")


@router.get("/status/{session_id}")
async def status(session_id: int):
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": s["status"], "error": s.get("error_message")}


@router.get("/log/{session_id}")
async def agent_log(session_id: int):
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    log = get_agent_log_live(session_id)
    return {"session_id": session_id, "status": s["status"], "log": log}


@router.get("/results/{session_id}")
async def results(session_id: int):
    data = get_results(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@router.get("/sessions")
async def sessions(limit: int = 100):
    return {"sessions": list_sessions(limit=limit)}


@router.get("/archetypes")
async def archetypes():
    from backend.database import get_all_pro_archetypes
    pros = get_all_pro_archetypes()
    return {"count": len(pros), "archetypes": pros}
