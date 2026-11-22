import random

import pytest

from rowbit.program import Command, Program, encode_instruction
from rowbit.sequencer import Sequencer

pytestmark = pytest.mark.hardware

# Legal DDR3-600 spacing in tCK (3.33 ns): tRCD 5, WR->PRE 14, RD->PRE 4, tRAS 11, tRP 5.
AFTER_ACT, AFTER_WRITE, AFTER_READ, AFTER_PRE = 8, 20, 12, 8


@pytest.fixture(scope="module")
def sequencer(board):
    return Sequencer(board.bus)


def random_locations(count=16):
    """Seed, distinct (bank, row, column) at burst starts, and data; new each run, since DRAM keeps old runs' data."""
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    locations = set()
    while len(locations) < count:
        locations.add((rng.randrange(8), rng.randrange(2**14), 8 * rng.randrange(128)))
    return seed, sorted(locations), [rng.getrandbits(128) for _ in range(count)]


def words_of(entry):
    return [entry >> (32 * lane) & 0xFFFFFFFF for lane in range(4)]


def controller_address(board, bank, row, column):
    """Where the controller's ROW_BANK_COL mapping puts this burst on the bus."""
    return board.bus.mems.main_ram.base + 16 * (row << 10 | bank << 7 | column >> 3)


def access(sequencer, locations, command, write_entries=()):
    program = Program(sequencer.read_phase, sequencer.write_phase)
    for bank, row, column in locations:
        program.command(Command.ACT, bank, row)
        program.wait(AFTER_ACT)
        program.command(command, bank, column)
        program.wait(AFTER_WRITE if command == Command.WR else AFTER_READ)
        program.command(Command.PRE, bank)
        program.wait(AFTER_PRE)
    return sequencer.run(program.instructions(), write_entries)


def burst_train(sequencer, bank, row, command, write_entries=(), count=16):
    """`count` bursts to consecutive columns of one row, tCCD (4 tCK, one sys cycle) apart."""
    program = Program(sequencer.read_phase, sequencer.write_phase)
    program.command(Command.ACT, bank, row)
    program.wait(AFTER_ACT)
    for burst in range(count):
        program.command(command, bank, 8 * burst)
        program.wait(3)
    program.wait(AFTER_WRITE if command == Command.WR else AFTER_READ)
    program.command(Command.PRE, bank)
    return sequencer.run(program.instructions(), write_entries)


def test_sequencer_writes_are_seen_by_controller(board, sequencer):
    seed, locations, data = random_locations()
    access(sequencer, locations, Command.WR, data)
    for location, expected in zip(locations, data):
        words = board.bus.read(controller_address(board, *location), length=4)
        assert words == words_of(expected), f"seed {seed}, location {location}"


def test_sequencer_reads_what_controller_wrote(board, sequencer):
    seed, locations, data = random_locations()
    for location, entry in zip(locations, data):
        board.bus.write(controller_address(board, *location), words_of(entry))
    assert access(sequencer, locations, Command.RD) == data, f"seed {seed}"


def outcome(call):
    """'ran' or the name of the exception the call raised."""
    try:
        call()
        return "ran"
    except Exception as error:
        return type(error).__name__


def test_write_entries_must_match_the_writes(sequencer):
    program = Program(sequencer.read_phase, sequencer.write_phase)
    program.command(Command.ACT)
    program.wait(AFTER_ACT)
    program.command(Command.WR)
    assert outcome(lambda: sequencer.run(program.instructions(), [])) == "ValueError"


def test_run_refuses_to_start_while_a_program_is_running(sequencer):
    long_program = [encode_instruction([], wait=2**28)]  # 3.6 s at 75 MHz
    assert outcome(lambda: sequencer.run(long_program, timeout=0.5)) == "TimeoutError"
    assert outcome(lambda: sequencer.run(Program(0, 0).instructions())) == "RuntimeError"
    sequencer.wait_until_idle(timeout=10)


def test_back_to_back_bursts_keep_their_own_data(board, sequencer):
    seed, locations, data = random_locations()
    bank, row, _ = locations[0]
    burst_train(sequencer, bank, row, Command.WR, data)
    written = [board.bus.read(controller_address(board, bank, row, 8 * burst), length=4) for burst in range(16)]
    assert written == [words_of(entry) for entry in data], f"seed {seed}"
    assert burst_train(sequencer, bank, row, Command.RD) == data, f"seed {seed}"
