import pytest

from rowbit.program import (ADDRESS_BITS, BANKS, PRECHARGE_ALL, PROGRAM_DEPTH, SLOTS, WRITE_DEPTH, Command,
                            Program)

READ_PHASE, WRITE_PHASE, CLOSE_DELAY = 2, 3, 16


def decode(instructions):
    """(tCK, command, bank, address) for every non-NOP slot, with the waits applied."""
    commands, cycle = [], 0
    for words in instructions:
        bits = sum(word << (32 * index) for index, word in enumerate(words))
        for slot in range(SLOTS):
            field = bits >> (24 * slot)
            if field & 0b111:
                commands.append((SLOTS * cycle + slot, Command(field & 0b111), field >> 3 & BANKS - 1,
                                 field >> 6 & 2**ADDRESS_BITS - 1))
        cycle += 1 + (bits >> 96)
    return commands


def test_commands_keep_their_spacing_and_end_with_precharge_all():
    program = Program(READ_PHASE, WRITE_PHASE, CLOSE_DELAY)
    program.command(Command.ACT, 3, 100)
    program.wait(40)
    program.command(Command.PRE, 3)
    assert decode(program.instructions()) == [
        (0, Command.ACT, 3, 100),
        (41, Command.PRE, 3, 0),
        (41 + CLOSE_DELAY, Command.PRE, 0, PRECHARGE_ALL),
    ]


def test_read_and_write_move_to_their_phase():
    program = Program(READ_PHASE, WRITE_PHASE, CLOSE_DELAY)
    program.command(Command.ACT, 1, 7)
    program.command(Command.RD, 1, 8)   # tCK 1 -> 2
    program.command(Command.WR, 1, 16)  # tCK 3 is already the write phase
    program.command(Command.RD, 1, 24)  # tCK 4 -> 6
    assert decode(program.instructions())[:4] == [
        (0, Command.ACT, 1, 7),
        (2, Command.RD, 1, 8),
        (3, Command.WR, 1, 16),
        (6, Command.RD, 1, 24),
    ]


def program_with_writes(count):
    program = Program(READ_PHASE, WRITE_PHASE, CLOSE_DELAY)
    for _ in range(count):
        program.command(Command.WR)
    return program


def test_write_data_limit():
    assert len(program_with_writes(WRITE_DEPTH).instructions()) == WRITE_DEPTH + 1
    with pytest.raises(ValueError):
        program_with_writes(WRITE_DEPTH + 1).instructions()


def test_instruction_limit():
    program = Program(READ_PHASE, WRITE_PHASE, CLOSE_DELAY)
    for _ in range(PROGRAM_DEPTH - 1):
        program.command(Command.PRE)
        program.wait(SLOTS - 1)  # one instruction each
    assert len(program.instructions()) == PROGRAM_DEPTH  # the PREs + the closing PREA
    program.command(Command.PRE)
    with pytest.raises(ValueError):
        program.instructions()
