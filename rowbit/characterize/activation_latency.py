# Reads with a chosen ACT->RD gap (tRCD), to find where the chip stops returning stored data.
from rowbit.program import SLOTS, Command, Program

SPEC_ACTIVATE_TO_READ = 5  # tRCD 13.75 ns at tCK 3.33 ns
# Legal DDR3-600 spacing in tCK: tRCD 5, WR->PRE 14, RD->PRE 4, tRP 5.
AFTER_ACT, AFTER_WRITE, AFTER_READ, AFTER_PRE = 8, 20, 12, 8


def write_bursts(sequencer, locations, entries):
    """Writes one 128-bit entry per (bank, row, column) with legal timing."""
    program = Program(sequencer.read_phase, sequencer.write_phase)
    for bank, row, column in locations:
        program.command(Command.ACT, bank, row)
        program.wait(AFTER_ACT)
        program.command(Command.WR, bank, column)
        program.wait(AFTER_WRITE)
        program.command(Command.PRE, bank)
        program.wait(AFTER_PRE)
    sequencer.run(program.instructions(), entries)


def read_bursts(sequencer, locations, activate_to_read):
    """Reads one burst per location with RD exactly `activate_to_read` tCK after ACT."""
    if activate_to_read < 1:
        raise ValueError(f"activate_to_read {activate_to_read} must be at least 1 tCK")
    program = Program(sequencer.read_phase, sequencer.write_phase)
    for bank, row, column in locations:
        # RD can only go on the read phase, so ACT goes activate_to_read before it.
        program.wait((sequencer.read_phase - activate_to_read - program.time) % SLOTS)
        program.command(Command.ACT, bank, row)
        program.wait(activate_to_read - 1)
        program.command(Command.RD, bank, column)
        program.wait(AFTER_READ)
        program.command(Command.PRE, bank)
        program.wait(AFTER_PRE)
    return sequencer.run(program.instructions())


def bit_errors(read, expected):
    return sum(bin(got ^ want).count("1") for got, want in zip(read, expected, strict=True))
