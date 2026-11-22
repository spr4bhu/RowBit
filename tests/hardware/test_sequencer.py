import random

import pytest

from rowbit.characterize.activation_latency import read_bursts, write_bursts
from rowbit.program import Command, encode_instruction
from rowbit.sequencer import LANES

pytestmark = pytest.mark.hardware


def random_locations(sequencer, count=16):
    """Seed, locations and data; new each run, since DRAM keeps old runs' data."""
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    return seed, sequencer.dram.random_locations(rng, count), [rng.getrandbits(128) for _ in range(count)]


def words_of(entry):
    return [entry >> (32 * lane) & 0xFFFFFFFF for lane in range(LANES)]


def controller_address(board, dram, bank, row, column):
    """Where the controller's ROW_BANK_COL mapping puts this burst on the bus (one 4-lane entry per burst)."""
    burst_bits = dram.column_bits - (dram.burst_length - 1).bit_length()
    burst = row << (dram.bank_bits + burst_bits) | bank << burst_bits | column // dram.burst_length
    return board.bus.mems.main_ram.base + 4 * LANES * burst


def read_at_spec(sequencer, locations):
    return read_bursts(sequencer, locations, sequencer.dram.activate_to_read)


def burst_train(sequencer, bank, row, command, write_entries=(), count=16):
    """`count` bursts to consecutive columns of one row, tCCD (BL/2 tCK) apart."""
    dram = sequencer.dram
    program = sequencer.program()
    program.command(Command.ACT, bank, row)
    program.wait(dram.activate_to_read - 1)
    for burst in range(count):
        program.command(command, bank, dram.burst_length * burst)
        program.wait(dram.burst_length // 2 - 1)
    to_precharge = dram.write_to_precharge if command == Command.WR else dram.read_to_precharge
    program.wait(max(0, to_precharge - dram.burst_length // 2))  # the cursor is already BL/2 past the last burst
    program.command(Command.PRE, bank)
    return sequencer.run(program.instructions(), write_entries)


def test_sequencer_writes_are_seen_by_controller(board, sequencer):
    seed, locations, data = random_locations(sequencer)
    write_bursts(sequencer, locations, data)
    for location, expected in zip(locations, data):
        words = board.bus.read(controller_address(board, sequencer.dram, *location), length=LANES)
        assert words == words_of(expected), f"seed {seed}, location {location}"


def test_sequencer_reads_what_controller_wrote(board, sequencer):
    seed, locations, data = random_locations(sequencer)
    for location, entry in zip(locations, data):
        board.bus.write(controller_address(board, sequencer.dram, *location), words_of(entry))
    assert read_at_spec(sequencer, locations) == data, f"seed {seed}"


def outcome(call):
    """'ran' or the name of the exception the call raised."""
    try:
        call()
        return "ran"
    except Exception as error:
        return type(error).__name__


def test_write_entries_must_match_the_writes(sequencer):
    program = sequencer.program()
    program.command(Command.ACT)
    program.wait(sequencer.dram.activate_to_read - 1)
    program.command(Command.WR)
    assert outcome(lambda: sequencer.run(program.instructions(), [])) == "ValueError"


def test_run_refuses_to_start_while_a_program_is_running(sequencer):
    long_program = [encode_instruction([], wait=2**28)]  # seconds at any sys clock this board can run
    assert outcome(lambda: sequencer.run(long_program, timeout=0.5)) == "TimeoutError"
    assert outcome(lambda: sequencer.run(sequencer.program().instructions())) == "RuntimeError"
    sequencer.wait_until_idle(timeout=10)


def test_back_to_back_bursts_keep_their_own_data(board, sequencer):
    seed, locations, data = random_locations(sequencer)
    bank, row, _ = locations[0]
    burst_train(sequencer, bank, row, Command.WR, data)
    columns = [sequencer.dram.burst_length * burst for burst in range(len(data))]
    written = [board.bus.read(controller_address(board, sequencer.dram, bank, row, column), length=LANES)
               for column in columns]
    assert written == [words_of(entry) for entry in data], f"seed {seed}"
    assert burst_train(sequencer, bank, row, Command.RD) == data, f"seed {seed}"
