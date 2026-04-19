"""
FastAPI backend — orchestrates the four agents for a Nuzlocke battle analysis session.

Flow:
  POST /session                   → create session, get session_id
  POST /session/{id}/upload/sav   → upload .sav → runs extracter agent
  POST /session/{id}/upload/gba   → upload .gba + optional trainer hint → runs researcher agent
  POST /session/{id}/analyze      → runs calculator + displayer → returns full display data
  GET  /session/{id}              → get current session state
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from src.core.session_manager import session_manager
from src.agents.extracter import extract_party
from src.agents.researcher import research_next_trainer
from src.agents.calculator import calculate_strategy
from src.agents.displayer import format_for_display

app = FastAPI(title="Nuzzy — Nuzlocke Battle Advisor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Session ────────────────────────────────────────────────────────────────

@app.post("/session")
def create_session():
    session = session_manager.create()
    return {"session_id": session.session_id}


@app.get("/session/{session_id}")
def get_session(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "has_player_data": session.player_data is not None,
        "has_trainer_data": session.trainer_data is not None,
        "has_strategy": session.strategy_data is not None,
        "display_data": session.display_data,
        "player_summary": session.player_data,
        "trainer_summary": session.trainer_data,
    }


# ── File uploads ───────────────────────────────────────────────────────────

@app.post("/session/{session_id}/upload/sav")
async def upload_sav(session_id: str, file: UploadFile = File(...)):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sav_bytes = await file.read()
    if len(sav_bytes) < 0x1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid .sav")

    result = extract_party(sav_bytes)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to parse .sav"))

    session.player_data = result["data"]
    session_manager.update(session)

    return {
        "success": True,
        "player_data": result["data"],
        "summary": result["summary"],
    }


@app.post("/session/{session_id}/upload/gba")
async def upload_gba(
    session_id: str,
    file: UploadFile = File(...),
    trainer_hint: Optional[str] = Form(default=None),
):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    rom_bytes = await file.read()
    if len(rom_bytes) < 0x100000:
        raise HTTPException(status_code=400, detail="File too small to be a valid .gba ROM")

    # Parse trainer_hint — could be a name or an integer index
    hint: str | int | None = None
    if trainer_hint:
        try:
            hint = int(trainer_hint)
        except ValueError:
            hint = trainer_hint

    result = research_next_trainer(rom_bytes, trainer_hint=hint)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to find trainer"))

    session.trainer_data = result["data"]
    session_manager.update(session)

    return {
        "success": True,
        "trainer_data": result["data"],
        "summary": result["summary"],
    }


# ── Analysis ───────────────────────────────────────────────────────────────

@app.post("/session/{session_id}/analyze")
def analyze(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_ready_for_calc:
        raise HTTPException(
            status_code=400,
            detail="Upload both .sav and .gba files before analyzing",
        )

    # Step 1: Calculate strategy
    calc_result = calculate_strategy(
        player_party=session.player_data["party"],
        trainer_party=session.trainer_data["party"],
    )
    if not calc_result["success"]:
        raise HTTPException(status_code=500, detail="Strategy calculation failed")

    session.strategy_data = calc_result["data"]

    # Step 2: Format for display
    display_result = format_for_display(
        player_data=session.player_data,
        trainer_data=session.trainer_data,
        strategy_data=calc_result["data"] or {},
    )
    if not display_result["success"]:
        raise HTTPException(status_code=500, detail="Display formatting failed")

    session.display_data = display_result["data"]
    session_manager.update(session)

    return {
        "success": True,
        "display_data": session.display_data,
    }


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
