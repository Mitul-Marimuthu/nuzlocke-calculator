"""
FastAPI backend — orchestrates the Nuzlocke battle analysis pipeline.

Upload flow:
  POST /session                   → create session, get session_id
  POST /session/{id}/upload/sav   → parse .sav directly → store player party
  POST /session/{id}/upload/gba   → parse .gba directly → store trainer data
  POST /session/{id}/analyze      → run calculator + displayer agents → strategy
  GET  /session/{id}              → current session state

Binary parsing (sav + gba) is done directly in Python — no LLM involvement.
The LLM is only used for strategy reasoning and display formatting.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from src.tools.sav_parser import parse_save, PokemonData
from src.tools.gba_parser import (
    get_trainer_by_index, search_trainers, get_all_trainers, TrainerData,
)
from src.core.session_manager import session_manager
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


# ── Helpers ────────────────────────────────────────────────────────────────

def _pokemon_to_dict(p: PokemonData) -> dict:
    return {
        "slot": p.slot,
        "nickname": p.nickname,
        "species_id": p.species_id,
        "species_name": p.species_name,
        "type1": p.type1,
        "type2": p.type2,
        "level": p.level,
        "current_hp": p.current_hp,
        "max_hp": p.max_hp,
        "atk": p.atk,
        "def": p.def_,
        "spa": p.spa,
        "spd": p.spd,
        "spe": p.spe,
        "moves": p.moves,
        "held_item_id": p.held_item_id,
        "experience": p.experience,
        "friendship": p.friendship,
        "ivs": p.ivs,
        "evs": p.evs,
        "is_fainted": p.is_fainted,
    }


def _trainer_to_dict(t: TrainerData) -> dict:
    return {
        "trainer_index": t.trainer_index,
        "name": t.name,
        "trainer_class": t.trainer_class,
        "is_double": t.is_double,
        "party": [
            {
                "species_id": p.species_id,
                "species_name": p.species_name,
                "type1": p.type1,
                "type2": p.type2,
                "level": p.level,
                "iv_value": p.iv_value,
                "held_item_id": p.held_item_id,
                "moves": p.moves,
                # Provide stat placeholders so the calculator has something to work with.
                # Trainer mons don't store live stats in the ROM — use level-scaled estimates.
                "current_hp": p.level * 2 + 20,
                "max_hp":     p.level * 2 + 20,
                "atk": max(10, p.level + p.iv_value),
                "def": max(10, p.level + p.iv_value),
                "spa": max(10, p.level + p.iv_value),
                "spd": max(10, p.level + p.iv_value),
                "spe": max(10, p.level + p.iv_value),
            }
            for p in t.party
        ],
    }


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


# ── File uploads (binary parsing — no LLM) ────────────────────────────────

@app.post("/session/{session_id}/upload/sav")
async def upload_sav(session_id: str, file: UploadFile = File(...)):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sav_bytes = await file.read()
    if len(sav_bytes) < 0x1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid .sav")

    try:
        save = parse_save(sav_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse .sav: {e}")

    player_data = {
        "trainer_name": save.trainer_name,
        "trainer_gender": save.trainer_gender,
        "trainer_id": save.trainer_id,
        "party": [_pokemon_to_dict(p) for p in save.party],
    }
    session.player_data = player_data
    session_manager.update(session)

    return {"success": True, "player_data": player_data}


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

    try:
        trainer: TrainerData | None = None

        if trainer_hint:
            trainer_hint = trainer_hint.strip()
            try:
                idx = int(trainer_hint)
                trainer = get_trainer_by_index(rom_bytes, idx)
            except ValueError:
                results = search_trainers(rom_bytes, trainer_hint)
                trainer = results[0] if results else None

        if trainer is None:
            all_trainers = get_all_trainers(rom_bytes)
            trainer = all_trainers[0] if all_trainers else None

        if trainer is None:
            raise HTTPException(status_code=422, detail="No valid trainer found in ROM")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse .gba: {e}")

    trainer_data = _trainer_to_dict(trainer)
    session.trainer_data = trainer_data
    session_manager.update(session)

    return {"success": True, "trainer_data": trainer_data}


# ── Analysis (LLM agents) ──────────────────────────────────────────────────

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

    calc = calculate_strategy(
        player_party=session.player_data["party"],
        trainer_party=session.trainer_data["party"],
    )
    if not calc["success"]:
        raise HTTPException(status_code=500, detail="Strategy calculation failed")

    session.strategy_data = calc["data"]

    display = format_for_display(
        player_data=session.player_data,
        trainer_data=session.trainer_data,
        strategy_data=calc["data"] or {},
    )
    if not display["success"]:
        raise HTTPException(status_code=500, detail=f"Display formatting failed: {display.get('error')}")

    session.display_data = display["data"]
    session_manager.update(session)

    return {"success": True, "display_data": session.display_data}


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
