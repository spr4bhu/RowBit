# Reads with a chosen ACT->RD gap (tRCD), to find where the chip stops returning stored data.
from rowbit.program import PROGRAM_DEPTH, SLOTS, Command

COMMANDS_PER_BURST = 3  # ACT, RD or WR, PRE
BURSTS_PER_PROGRAM = (PROGRAM_DEPTH - 1) // COMMANDS_PER_BURST  # one instruction per command at most, plus PREA


def write_bursts(sequencer, locations, entries):
    """Writes one 128-bit entry per (bank, row, column) with legal timing."""
    dram = sequencer.dram
    program = sequencer.program()
    for bank, row, column in locations:
        program.command(Command.ACT, bank, row)
        program.wait(dram.activate_to_read - 1)
        program.command(Command.WR, bank, column)
        program.wait(max(dram.write_to_precharge, dram.activate_to_precharge - dram.activate_to_read) - 1)
        program.command(Command.PRE, bank)
        program.wait(dram.precharge_to_activate - 1)
    sequencer.run(program.instructions(), entries)


def read_bursts(sequencer, locations, activate_to_read):
    """Reads one burst per location with RD exactly `activate_to_read` tCK after ACT; all else legal."""
    if activate_to_read < 1:
        raise ValueError(f"activate_to_read {activate_to_read} must be at least 1 tCK")
    dram = sequencer.dram
    program = sequencer.program()
    for bank, row, column in locations:
        # RD can only go on the read phase, so ACT goes activate_to_read before it.
        program.wait((sequencer.read_phase - activate_to_read - program.time) % SLOTS)
        program.command(Command.ACT, bank, row)
        program.wait(activate_to_read - 1)
        program.command(Command.RD, bank, column)
        program.wait(max(dram.read_to_precharge, dram.activate_to_precharge - activate_to_read) - 1)
        program.command(Command.PRE, bank)
        program.wait(dram.precharge_to_activate - 1)
    return sequencer.run(program.instructions())


def bit_errors(read, expected):
    return sum(bin(got ^ want).count("1") for got, want in zip(read, expected, strict=True))
