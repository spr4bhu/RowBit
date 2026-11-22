# Subarray map: row r starts a subarray where copying r-1 onto r fails.
from rowbit.characterize.activation_latency import BURSTS_PER_PROGRAM, read_bursts, write_bursts
from rowbit.operations.copy import copy_rows
from rowbit.sequencer import LANES

SUBARRAY_ROWS = 512  # measured on this chip; repaired rows add extra starts


def subarray_starts(sequencer, bank, rows, rng):
    """Rows of the consecutive `rows` (after the first) that a copy from the row before doesn't reach."""
    rows = list(rows)
    starts = []
    # A failed copy into a repaired row corrupts its pair partner, so one parity per pass.
    for parity in (0, 1):
        entries = {row: rng.getrandbits(32 * LANES) for row in rows}
        write_first_bursts(sequencer, bank, rows, list(entries.values()))
        destinations = [row for row in rows[1:] if row % 2 == parity]
        copy_rows(sequencer, bank, [(row - 1, row) for row in destinations])
        read = read_first_bursts(sequencer, bank, destinations)
        starts += [row for row, entry in zip(destinations, read) if entry != entries[row - 1]]
    return sorted(starts)


def write_first_bursts(sequencer, bank, rows, entries):
    for start in range(0, len(rows), BURSTS_PER_PROGRAM):
        locations = [(bank, row, 0) for row in rows[start:start + BURSTS_PER_PROGRAM]]
        write_bursts(sequencer, locations, entries[start:start + BURSTS_PER_PROGRAM])


def read_first_bursts(sequencer, bank, rows):
    read = []
    for start in range(0, len(rows), BURSTS_PER_PROGRAM):
        locations = [(bank, row, 0) for row in rows[start:start + BURSTS_PER_PROGRAM]]
        read += read_bursts(sequencer, locations, sequencer.dram.activate_to_read)
    return read
