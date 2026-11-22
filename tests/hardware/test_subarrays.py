import random

import pytest

from rowbit.characterize.subarrays import SUBARRAY_ROWS, subarray_starts
from rowbit.operations.copy import copy_row
from rowbit.sequencer import LANES

pytestmark = pytest.mark.hardware


@pytest.fixture(scope="module")
def measured(sequencer):
    """Subarray starts in two subarrays' worth of rows of a random bank, across two boundaries."""
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    dram = sequencer.dram
    bank = rng.randrange(dram.banks)
    first = SUBARRAY_ROWS * rng.randrange(1, dram.rows // SUBARRAY_ROWS - 1) - SUBARRAY_ROWS // 2
    rows = range(first, first + 2 * SUBARRAY_ROWS)
    return seed, rng, bank, rows, subarray_starts(sequencer, bank, rows, rng)


def copies(board, sequencer, rng, bank, source, destination):
    """True if `destination` ends up with `source`'s data, checked over the whole row."""
    words = LANES * sequencer.dram.columns // sequencer.dram.burst_length
    data = [rng.getrandbits(32) for _ in range(words)]
    board.bus.write(sequencer.controller_address(bank, source), data)
    board.bus.write(sequencer.controller_address(bank, destination), [word ^ 0xFFFFFFFF for word in data])
    copy_row(sequencer, bank, source, destination)
    return board.bus.read(sequencer.controller_address(bank, destination), length=words) == data


def test_every_subarray_boundary_is_found(measured):
    seed, _, bank, rows, starts = measured
    boundaries = [row for row in rows[1:] if row % SUBARRAY_ROWS == 0]
    assert set(boundaries) <= set(starts), f"seed {seed}, bank {bank}, starts {starts}"


def test_single_copies_work_inside_a_subarray_and_fail_across(board, sequencer, measured):
    seed, rng, bank, rows, starts = measured
    where = f"seed {seed}, bank {bank}, starts {starts}"
    for start in starts:
        assert not copies(board, sequencer, rng, bank, start - 1, start), f"{where}: {start - 1} -> {start} copied"
    edges = [rows[0]] + starts + [rows[-1] + 1]
    segments = [range(low, high) for low, high in zip(edges, edges[1:]) if high - low > 1]
    assert segments, f"{where}: no two neighbouring rows copy"
    for _ in range(8):
        source, destination = rng.sample(rng.choice(segments), 2)
        assert copies(board, sequencer, rng, bank, source, destination), f"{where}: {source} -> {destination}"
