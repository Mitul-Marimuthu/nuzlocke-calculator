"""Unit tests for the SAV parser — using a minimal synthetic save block."""

import struct
import pytest
from src.tools.sav_parser import (
    _decode_gen3_string,
    _decrypt_substructures,
    SAVE_MAGIC,
    SECTION_SIZE,
    SECTION_MAGIC_OFF,
    SECTION_ID_OFF,
    SECTION_INDEX_OFF,
    SUBSTRUCTURE_ORDERS,
)


def test_decode_gen3_string_basic():
    # 'A' = 0xBB, 'B' = 0xBC, terminator = 0xFF
    data = bytes([0xBB, 0xBC, 0xFF, 0x00])
    assert _decode_gen3_string(data, 4) == "AB"


def test_decode_gen3_string_max_len():
    data = bytes([0xBB] * 10)  # no terminator
    result = _decode_gen3_string(data, 5)
    assert result == "AAAAA"


def test_substructure_order_length():
    assert len(SUBSTRUCTURE_ORDERS) == 24
    for order in SUBSTRUCTURE_ORDERS:
        assert set(order) == {"G", "A", "E", "M"}
        assert len(order) == 4


def test_substructure_orders_unique():
    assert len(set(SUBSTRUCTURE_ORDERS)) == 24


def test_decrypt_substructures_zero_key():
    # PID=0, OTID=0 → key=0 → data is unchanged
    raw = bytearray(100)
    # Set a known species ID in the Growth substructure at correct offset
    # PID%24=0 → order GAEM → G is substructure 0 (bytes 0x20-0x2B)
    species_id = 25  # Pikachu
    struct.pack_into("<H", raw, 0x20, species_id)
    subs = _decrypt_substructures(bytes(raw))
    parsed_species = struct.unpack_from("<H", subs["G"], 0)[0]
    assert parsed_species == species_id


def test_decrypt_substructures_nonzero_key():
    pid = 0xDEADBEEF
    ot_id = 0x12345678
    key = pid ^ ot_id

    raw = bytearray(100)
    struct.pack_into("<I", raw, 0, pid)
    struct.pack_into("<I", raw, 4, ot_id)

    species_id = 6  # Charizard
    # PID % 24 = 0xDEADBEEF % 24
    order_idx = pid % 24
    order = SUBSTRUCTURE_ORDERS[order_idx]
    g_sub_idx = order.index("G")

    # Encrypt species into the correct substructure position
    growth_off = 0x20 + g_sub_idx * 12
    raw_species_word = species_id ^ key
    struct.pack_into("<I", raw, growth_off, raw_species_word)

    subs = _decrypt_substructures(bytes(raw))
    parsed_species = struct.unpack_from("<H", subs["G"], 0)[0]
    assert parsed_species == species_id
