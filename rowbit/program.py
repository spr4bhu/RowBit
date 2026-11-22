from enum import IntEnum

SLOTS = 4  # DRAM clocks per sys clock
WORDS_PER_INSTRUCTION = 4
BANKS = 8
ADDRESS_BITS = 14


class Command(IntEnum):
    NOP = 0
    ACT = 1
    PRE = 2
    RD = 3
    WR = 4
    REF = 5
    ZQCS = 6


def encode_slot(command, bank=0, address=0):
    if not 0 <= bank < BANKS or not 0 <= address < 2**ADDRESS_BITS:
        raise ValueError(f"bank {bank} or address {address:#x} out of range")
    return int(Command(command)) | (bank << 3) | (address << 6)


def encode_instruction(slots, wait=0):
    """slots: up to 4 (command, bank, address) tuples, one per DRAM clock; wait: idle sys cycles after."""
    if len(slots) > SLOTS or not 0 <= wait < 2**32:
        raise ValueError(f"{len(slots)} slots or wait {wait} out of range")
    bits = 0
    for index, slot in enumerate(slots):
        bits |= encode_slot(*slot) << (24 * index)
    bits |= wait << 96
    return [(bits >> (32 * word)) & 0xFFFFFFFF for word in range(WORDS_PER_INSTRUCTION)]
