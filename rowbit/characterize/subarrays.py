# Subarray map: row r starts a subarray where copying r-1 onto r fails.
import json
import os
import random

from rowbit.board import ROOT, Board
from rowbit.characterize.activation_latency import BURSTS_PER_PROGRAM, read_bursts, write_bursts
from rowbit.operations.copy import copy_rows
from rowbit.sequencer import LANES, Sequencer

SUBARRAY_ROWS = 512  # measured on this chip; repaired rows add extra starts
MAP_DIRECTORY = os.path.join(ROOT, "results")


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


def measure_map(sequencer, rng):
    """Subarray starts of every bank over the whole chip (takes minutes)."""
    dram = sequencer.dram
    return [subarray_starts(sequencer, bank, range(dram.rows), rng) for bank in range(dram.banks)]


def map_path(serial, directory=MAP_DIRECTORY):
    return os.path.join(directory, f"subarrays-{serial}.json")


def save_map(serial, starts, seed, directory=MAP_DIRECTORY):
    os.makedirs(directory, exist_ok=True)
    with open(map_path(serial, directory), "w") as file:
        json.dump({"seed": seed, "starts": starts}, file)


def load_map(serial, directory=MAP_DIRECTORY):
    """This board's saved starts per bank, or None if it was never mapped."""
    try:
        with open(map_path(serial, directory)) as file:
            return json.load(file)["starts"]
    except FileNotFoundError:
        return None


def known_starts(serial, dram, directory=MAP_DIRECTORY):
    """Starts per bank from this board's saved map, else the plain grid."""
    starts = load_map(serial, directory)
    if starts is None:
        return [list(range(SUBARRAY_ROWS, dram.rows, SUBARRAY_ROWS)) for _ in range(dram.banks)]
    if len(starts) != dram.banks or any(row >= dram.rows for bank in starts for row in bank):
        raise ValueError(f"{map_path(serial, directory)} doesn't fit {dram.banks} banks of {dram.rows} rows")
    return starts


def blocks_inside_subarrays(starts, bank_rows, size):
    """First rows of the `size`-aligned blocks of a bank that no subarray start splits."""
    starts = set(starts)
    return [first for first in range(0, bank_rows, size) if starts.isdisjoint(range(first + 1, first + size))]


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


def main():
    seed = random.randrange(2**32)
    board = Board()
    board.program()
    board.connect()
    try:
        board.read_console("litex> ")
        starts = measure_map(Sequencer(board.bus), random.Random(seed))
    finally:
        board.close()
    save_map(board.serial, starts, seed)
    print(f"saved {map_path(board.serial)} (seed {seed})")
    for bank, bank_starts in enumerate(starts):
        off_grid = [row for row in bank_starts if row % SUBARRAY_ROWS]
        print(f"bank {bank}: {len(bank_starts)} starts; off the {SUBARRAY_ROWS}-row grid: {off_grid or 'none'}")


if __name__ == "__main__":
    main()
