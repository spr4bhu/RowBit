# In-DRAM row copy (RowClone): ACT the source, PRE, then ACT the destination before the bitlines precharge.
from rowbit.program import Command

COPY_PRECHARGE_TO_ACTIVATE = 2  # tCK; measured on this chip at tCK 2.86 ns (1 tCK: ACT ignored, 3: too late)


def copy_row(sequencer, bank, source, destination):
    """Copies row `source` onto row `destination` of `bank`; both must be in the same subarray."""
    dram = sequencer.dram
    program = sequencer.program()
    program.command(Command.ACT, bank, source)
    program.wait(dram.activate_to_precharge - 1)  # source fully restored onto the bitlines
    program.command(Command.PRE, bank)
    program.wait(COPY_PRECHARGE_TO_ACTIVATE - 1)
    program.command(Command.ACT, bank, destination)
    program.wait(dram.activate_to_precharge - 1)  # destination cells take the bitline values
    program.command(Command.PRE, bank)
    sequencer.run(program.instructions())
