"""
Parses Pokémon Emerald (GBA) .gba ROM files to extract trainer data.
Uses the Emerald (US) trainer table offset and ROM pointer arithmetic.

Trainer data reference:
  https://bulbapedia.bulbagarden.net/wiki/Trainer_data_structure_(Generation_III)
"""

import struct
from dataclasses import dataclass
from typing import Optional
from src.data import get_species, get_move

# ── ROM constants (Pokémon Emerald US, 1.0) ────────────────────────────────
GBA_ROM_POINTER_BASE = 0x08000000
TRAINER_TABLE_OFFSET = 0x3203BC    # start of trainer data table in ROM
TRAINER_COUNT = 855                 # total trainers in Emerald
TRAINER_STRUCT_SIZE = 40            # fixed-size trainer header

# Trainer header layout (40 bytes)
PARTY_FLAGS_OFF = 0    # u8  bit0=has_items, bit1=has_custom_moves
TRAINER_CLASS_OFF = 1  # u8
MUSIC_GENDER_OFF = 2   # u8
SPRITE_OFF = 3         # u8
NAME_OFF = 4           # 12 bytes, Gen 3 encoded
ITEMS_OFF = 16         # 4× u16 (trainer's bag items, rarely used)
IS_DOUBLE_OFF = 24     # u32
AI_FLAGS_OFF = 28      # u32
PARTY_COUNT_OFF = 32   # u8
PARTY_PTR_OFF = 36     # u32 ROM pointer

# Party member sizes (bytes) depending on party_flags
PARTY_BASE_SIZE = 8    # IVs(2) + Level(2) + Species(2) + Padding(2)
PARTY_ITEM_EXTRA = 0   # item replaces padding — same 8 bytes
PARTY_MOVES_EXTRA = 8  # adds 4× u16 moves = 8 extra bytes

# Gen 3 character decoding (reused from sav_parser)
_GEN3_CHARS: dict[int, str] = {}
for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _GEN3_CHARS[0xBB + i] = c
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    _GEN3_CHARS[0xD5 + i] = c
for i, c in enumerate("0123456789"):
    _GEN3_CHARS[0xA1 + i] = c
_GEN3_CHARS[0x00] = " "
_GEN3_CHARS[0xFF] = "\x00"

_TRAINER_CLASSES = {
    0x01: "PKMN Trainer", 0x02: "Aqua Admin", 0x05: "Beauty",
    0x09: "Bug Catcher", 0x0A: "Bug Maniac", 0x0C: "Camper",
    0x0F: "Cooltrainer", 0x11: "Dragon Tamer", 0x12: "Elite Four",
    0x13: "Expert", 0x14: "Fisherman", 0x18: "Gym Leader",
    0x19: "Hiker", 0x1D: "Lady", 0x1E: "Lass",
    0x22: "Picnicker", 0x23: "Pokéfan", 0x24: "Pokémaniac",
    0x27: "Psychic", 0x29: "Rival", 0x2A: "Ruin Maniac",
    0x2B: "Sailor", 0x2D: "Swimmer♂", 0x2E: "Swimmer♀",
    0x30: "Tuber♂", 0x31: "Tuber♀", 0x32: "Twins",
    0x33: "Winstrate", 0x35: "Young Couple", 0x36: "Youngster",
}


def _decode_gen3_string(data: bytes, max_len: int) -> str:
    result = []
    for b in data[:max_len]:
        if b == 0xFF:
            break
        result.append(_GEN3_CHARS.get(b, "?"))
    return "".join(result).strip()


def _rom_ptr_to_offset(ptr: int) -> int:
    return ptr - GBA_ROM_POINTER_BASE


@dataclass
class TrainerPokemon:
    species_id: int
    species_name: str
    type1: str
    type2: Optional[str]
    level: int
    iv_value: int       # 0-31, all stats share the same IV in trainer mons
    held_item_id: Optional[int]
    moves: list[dict]   # list of move dicts (empty = default level-up moves)


@dataclass
class TrainerData:
    trainer_index: int
    name: str
    trainer_class: str
    is_double: bool
    party: list[TrainerPokemon]


def _parse_trainer_pokemon(
    rom: bytes,
    party_ptr: int,
    party_count: int,
    party_flags: int,
) -> list[TrainerPokemon]:
    has_items = bool(party_flags & 0x01)
    has_moves = bool(party_flags & 0x02)
    entry_size = PARTY_BASE_SIZE + (PARTY_MOVES_EXTRA if has_moves else 0)

    party: list[TrainerPokemon] = []
    for i in range(party_count):
        off = party_ptr + i * entry_size
        if off + entry_size > len(rom):
            break

        iv_raw = struct.unpack_from("<H", rom, off)[0]
        level = struct.unpack_from("<H", rom, off + 2)[0]
        species_id = struct.unpack_from("<H", rom, off + 4)[0]
        item_id = struct.unpack_from("<H", rom, off + 6)[0] if has_items else None

        moves: list[dict] = []
        if has_moves:
            for m in range(4):
                mid = struct.unpack_from("<H", rom, off + 8 + m * 2)[0]
                if mid == 0:
                    continue
                md = get_move(mid)
                moves.append({
                    "id": mid,
                    "name": md["name"] if md else f"Move#{mid}",
                    "type": md["type"] if md else "Normal",
                    "power": md["power"] if md else None,
                    "accuracy": md["accuracy"] if md else None,
                    "damage_class": md["damage_class"] if md else "physical",
                })

        species = get_species(species_id)
        party.append(TrainerPokemon(
            species_id=species_id,
            species_name=species["name"] if species else f"Species#{species_id}",
            type1=species["type1"] if species else "Normal",
            type2=species.get("type2") if species else None,
            level=level,
            iv_value=iv_raw & 0x1F,
            held_item_id=item_id,
            moves=moves,
        ))

    return party


def _parse_trainer(rom: bytes, index: int) -> Optional[TrainerData]:
    off = TRAINER_TABLE_OFFSET + index * TRAINER_STRUCT_SIZE
    if off + TRAINER_STRUCT_SIZE > len(rom):
        return None

    party_flags = rom[off + PARTY_FLAGS_OFF]
    trainer_class_id = rom[off + TRAINER_CLASS_OFF]
    name_bytes = rom[off + NAME_OFF: off + NAME_OFF + 12]
    name = _decode_gen3_string(name_bytes, 12)
    is_double = struct.unpack_from("<I", rom, off + IS_DOUBLE_OFF)[0] != 0
    party_count = rom[off + PARTY_COUNT_OFF]
    party_ptr_raw = struct.unpack_from("<I", rom, off + PARTY_PTR_OFF)[0]

    if party_ptr_raw < GBA_ROM_POINTER_BASE:
        return None
    party_ptr = _rom_ptr_to_offset(party_ptr_raw)
    if party_ptr + party_count * PARTY_BASE_SIZE > len(rom):
        return None

    party = _parse_trainer_pokemon(rom, party_ptr, party_count, party_flags)
    trainer_class = _TRAINER_CLASSES.get(trainer_class_id, f"Trainer#{trainer_class_id}")

    return TrainerData(
        trainer_index=index,
        name=name,
        trainer_class=trainer_class,
        is_double=is_double,
        party=party,
    )


# ── Public API ─────────────────────────────────────────────────────────────

def get_all_trainers(rom_bytes: bytes) -> list[TrainerData]:
    """Return all parseable trainers from the ROM."""
    trainers = []
    for i in range(TRAINER_COUNT):
        t = _parse_trainer(rom_bytes, i)
        if t and t.name and t.party:
            trainers.append(t)
    return trainers


def get_trainer_by_index(rom_bytes: bytes, index: int) -> Optional[TrainerData]:
    return _parse_trainer(rom_bytes, index)


def search_trainers(rom_bytes: bytes, name: str) -> list[TrainerData]:
    """Find trainers whose name contains the given string (case-insensitive)."""
    name_lower = name.lower()
    results = []
    for i in range(TRAINER_COUNT):
        t = _parse_trainer(rom_bytes, i)
        if t and name_lower in t.name.lower():
            results.append(t)
    return results
