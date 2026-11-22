# In-DRAM row copy (RowClone): ACT the source, PRE, then ACT the destination before the bitlines precharge.
from rowbit.program import PROGRAM_DEPTH, Command

COPY_PRECHARGE_TO_ACTIVATE = 2  # tCK; measured on this chip at tCK 2.86 ns (1 tCK: ACT ignored, 3: too late)
COMMANDS_PER_COPY = 4
COPIES_PER_PROGRAM = (PROGRAM_DEPTH - 1) // COMMANDS_PER_COPY  # one instruction per command at most, plus PREA


def copy_row(sequencer, bank, source, destination):
    """Copies row `source` onto row `destination` of `bank`; both must be in the same subarray."""
    init_rows(sequencer, bank, source, [destination])


def init_rows(sequencer, bank, pattern_row, rows):
    """Copies `pattern_row` onto every row in `rows` of `bank`; all must be in its subarray."""
    rows = list(rows)
    for start in range(0, len(rows), COPIES_PER_PROGRAM):
        program = sequencer.program()
        for row in rows[start:start + COPIES_PER_PROGRAM]:
            add_copy(program, sequencer.dram, bank, pattern_row, row)
        sequencer.run(program.instructions())


def add_copy(program, dram, bank, source, destination):
    program.command(Command.ACT, bank, source)
    program.wait(dram.activate_to_precharge - 1)  # source fully restored onto the bitlines
    program.command(Command.PRE, bank)
    program.wait(COPY_PRECHARGE_TO_ACTIVATE - 1)
    program.command(Command.ACT, bank, destination)
    program.wait(dram.activate_to_precharge - 1)  # destination cells take the bitline values
    program.command(Command.PRE, bank)
    program.wait(dram.precharge_to_activate - 1)  # legal tRP before the next copy
