"""
Parses Pokémon Emerald (GBA) .sav files.
Save format reference: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)
"""

import struct
from dataclasses import dataclass, field
from typing import Optional
from src.data import get_species, get_move

# ── Save layout constants ──────────────────────────────────────────────────
SECTION_SIZE = 0x1000          # 4096 bytes per section
NUM_SECTIONS = 14
SAVE_SLOT_SIZE = NUM_SECTIONS * SECTION_SIZE   # 57344 bytes per slot

SECTION_DATA_SIZE = 0xFF4      # usable data bytes per section
SECTION_FOOTER_OFF = 0xFF4     # footer starts here
SECTION_ID_OFF = 0xFF4         # section ID   (2 bytes)
SECTION_CHECKSUM_OFF = 0xFF6   # checksum     (2 bytes)
SECTION_MAGIC_OFF = 0xFF8      # 0x08012025   (4 bytes)
SECTION_INDEX_OFF = 0xFFC      # save index   (4 bytes)

SAVE_MAGIC = 0x08012025

# Section IDs
SEC_TRAINER_INFO = 0
SEC_TEAM_ITEMS = 1

# Offsets within section 1 (Team/Items)
TEAM_COUNT_OFF = 0x234   # u32 — number of Pokémon in party
TEAM_DATA_OFF = 0x238    # start of 6 × 100-byte party structs

# Offsets within section 0 (Trainer Info) for Emerald
TRAINER_NAME_OFF = 0x00   # 7 bytes, Gen 3 encoded
TRAINER_GENDER_OFF = 0x08 # 1 byte (0=male, 1=female)
TRAINER_ID_OFF = 0x0A     # u16 public ID
TRAINER_SECRET_OFF = 0x0C # u16 secret ID

# Pokémon data structure (party slot = 100 bytes)
POKEMON_SIZE = 100
POKEMON_DATA_OFF = 0x20    # start of 48-byte encrypted data block
POKEMON_STATUS_OFF = 0x50  # start of unencrypted status/stats (party only)

# Substructure permutation order indexed by (PID % 24)
_S = "GAEM"
SUBSTRUCTURE_ORDERS = [
    "GAEM", "GAME", "GEAM", "GEMA", "GMAE", "GMEA",
    "AGEM", "AGME", "AEGM", "AEMG", "AMGE", "AMEG",
    "EGAM", "EGMA", "EAGM", "EAMG", "EMGA", "EMAG",
    "MGAE", "MGEA", "MAGE", "MAEG", "MEGA", "MEAG",
]

# Gen 3 character table (byte → char)
_GEN3_CHARS: dict[int, str] = {}
_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_lower = "abcdefghijklmnopqrstuvwxyz"
_digits = "0123456789"
for i, c in enumerate(_upper):
    _GEN3_CHARS[0xBB + i] = c
for i, c in enumerate(_lower):
    _GEN3_CHARS[0xD5 + i] = c
for i, c in enumerate(_digits):
    _GEN3_CHARS[0xA1 + i] = c
_GEN3_CHARS[0x00] = " "
_GEN3_CHARS[0xFF] = "\x00"  # string terminator


def _decode_gen3_string(data: bytes, max_len: int) -> str:
    result = []
    for b in data[:max_len]:
        if b == 0xFF:
            break
        result.append(_GEN3_CHARS.get(b, "?"))
    return "".join(result).strip()


# ── Section handling ───────────────────────────────────────────────────────

@dataclass
class SaveSection:
    section_id: int
    data: bytes
    save_index: int


def _parse_sections(raw: bytes, slot_offset: int) -> dict[int, SaveSection]:
    sections: dict[int, SaveSection] = {}
    for i in range(NUM_SECTIONS):
        off = slot_offset + i * SECTION_SIZE
        section_raw = raw[off: off + SECTION_SIZE]

        sec_id = struct.unpack_from("<H", section_raw, SECTION_ID_OFF)[0]
        magic = struct.unpack_from("<I", section_raw, SECTION_MAGIC_OFF)[0]
        save_idx = struct.unpack_from("<I", section_raw, SECTION_INDEX_OFF)[0]

        if magic != SAVE_MAGIC:
            continue

        sections[sec_id] = SaveSection(
            section_id=sec_id,
            data=section_raw[:SECTION_DATA_SIZE],
            save_index=save_idx,
        )
    return sections


def _active_slot(raw: bytes) -> dict[int, SaveSection]:
    slot0 = _parse_sections(raw, 0)
    slot1 = _parse_sections(raw, SAVE_SLOT_SIZE)

    if not slot0 and not slot1:
        raise ValueError("No valid save data found in file")
    if not slot0:
        return slot1
    if not slot1:
        return slot0

    idx0 = slot0[SEC_TRAINER_INFO].save_index if SEC_TRAINER_INFO in slot0 else -1
    idx1 = slot1[SEC_TRAINER_INFO].save_index if SEC_TRAINER_INFO in slot1 else -1
    return slot0 if idx0 >= idx1 else slot1


# ── Pokémon decryption ─────────────────────────────────────────────────────

def _decrypt_substructures(raw_pokemon: bytes) -> dict[str, bytes]:
    pid = struct.unpack_from("<I", raw_pokemon, 0x00)[0]
    ot_id = struct.unpack_from("<I", raw_pokemon, 0x04)[0]
    key = pid ^ ot_id

    encrypted = raw_pokemon[POKEMON_DATA_OFF: POKEMON_DATA_OFF + 48]
    decrypted = bytearray()
    for i in range(0, 48, 4):
        word = struct.unpack_from("<I", encrypted, i)[0]
        decrypted += struct.pack("<I", word ^ key)

    order = SUBSTRUCTURE_ORDERS[pid % 24]
    subs: dict[str, bytes] = {}
    for idx, letter in enumerate(order):
        subs[letter] = bytes(decrypted[idx * 12: idx * 12 + 12])
    return subs


@dataclass
class PokemonData:
    slot: int
    nickname: str
    species_id: int
    species_name: str
    type1: str
    type2: Optional[str]
    level: int
    current_hp: int
    max_hp: int
    atk: int
    def_: int
    spa: int
    spd: int
    spe: int
    moves: list[dict]
    held_item_id: int
    experience: int
    friendship: int
    ivs: dict[str, int]
    evs: dict[str, int]
    is_fainted: bool


def _parse_pokemon(raw_pokemon: bytes, slot: int) -> Optional[PokemonData]:
    pid = struct.unpack_from("<I", raw_pokemon, 0x00)[0]
    if pid == 0:
        return None

    subs = _decrypt_substructures(raw_pokemon)
    g = subs["G"]  # Growth
    a = subs["A"]  # Attacks
    e = subs["E"]  # EVs
    m = subs["M"]  # Misc

    # Growth substructure
    species_id = struct.unpack_from("<H", g, 0)[0]
    held_item_id = struct.unpack_from("<H", g, 2)[0]
    experience = struct.unpack_from("<I", g, 4)[0]
    friendship = g[9]

    # Attacks substructure
    move_ids = [struct.unpack_from("<H", a, i * 2)[0] for i in range(4)]
    move_pps = [a[8 + i] for i in range(4)]

    moves = []
    for mid, pp in zip(move_ids, move_pps):
        if mid == 0:
            continue
        move_data = get_move(mid)
        moves.append({
            "id": mid,
            "name": move_data["name"] if move_data else f"Move#{mid}",
            "type": move_data["type"] if move_data else "Normal",
            "power": move_data["power"] if move_data else None,
            "accuracy": move_data["accuracy"] if move_data else None,
            "pp": pp,
            "damage_class": move_data["damage_class"] if move_data else "physical",
        })

    # EV substructure
    evs = {"hp": e[0], "atk": e[1], "def": e[2], "spe": e[3], "spa": e[4], "spd": e[5]}

    # Misc substructure — packed IVs (5 bits each)
    iv_word = struct.unpack_from("<I", m, 4)[0]
    ivs = {
        "hp":  (iv_word >> 0)  & 0x1F,
        "atk": (iv_word >> 5)  & 0x1F,
        "def": (iv_word >> 10) & 0x1F,
        "spe": (iv_word >> 15) & 0x1F,
        "spa": (iv_word >> 20) & 0x1F,
        "spd": (iv_word >> 25) & 0x1F,
    }

    # Status / battle stats (party only, unencrypted at 0x50)
    status_raw = raw_pokemon[POKEMON_STATUS_OFF:]
    level = status_raw[4]
    cur_hp = struct.unpack_from("<H", status_raw, 6)[0]
    max_hp = struct.unpack_from("<H", status_raw, 8)[0]
    atk = struct.unpack_from("<H", status_raw, 10)[0]
    def_ = struct.unpack_from("<H", status_raw, 12)[0]
    spe = struct.unpack_from("<H", status_raw, 14)[0]
    spa = struct.unpack_from("<H", status_raw, 16)[0]
    spd = struct.unpack_from("<H", status_raw, 18)[0]

    nickname = _decode_gen3_string(raw_pokemon[0x08:0x12], 10)

    species = get_species(species_id)
    species_name = species["name"] if species else f"Species#{species_id}"
    type1 = species["type1"] if species else "Normal"
    type2 = species.get("type2") if species else None

    return PokemonData(
        slot=slot,
        nickname=nickname,
        species_id=species_id,
        species_name=species_name,
        type1=type1,
        type2=type2,
        level=level,
        current_hp=cur_hp,
        max_hp=max_hp,
        atk=atk,
        def_=def_,
        spa=spa,
        spd=spd,
        spe=spe,
        moves=moves,
        held_item_id=held_item_id,
        experience=experience,
        friendship=friendship,
        ivs=ivs,
        evs=evs,
        is_fainted=(cur_hp == 0),
    )


# ── Public API ─────────────────────────────────────────────────────────────

@dataclass
class SaveData:
    trainer_name: str
    trainer_gender: str
    trainer_id: int
    party: list[PokemonData]


def parse_save(sav_bytes: bytes) -> SaveData:
    sections = _active_slot(sav_bytes)

    sec0 = sections[SEC_TRAINER_INFO].data
    trainer_name = _decode_gen3_string(sec0[TRAINER_NAME_OFF: TRAINER_NAME_OFF + 7], 7)
    trainer_gender = "Female" if sec0[TRAINER_GENDER_OFF] == 1 else "Male"
    trainer_id = struct.unpack_from("<H", sec0, TRAINER_ID_OFF)[0]

    sec1 = sections[SEC_TEAM_ITEMS].data
    team_count = struct.unpack_from("<I", sec1, TEAM_COUNT_OFF)[0]
    team_count = min(team_count, 6)

    party: list[PokemonData] = []
    for i in range(team_count):
        off = TEAM_DATA_OFF + i * POKEMON_SIZE
        raw_poke = sec1[off: off + POKEMON_SIZE]
        poke = _parse_pokemon(raw_poke, i)
        if poke:
            party.append(poke)

    return SaveData(
        trainer_name=trainer_name,
        trainer_gender=trainer_gender,
        trainer_id=trainer_id,
        party=party,
    )
