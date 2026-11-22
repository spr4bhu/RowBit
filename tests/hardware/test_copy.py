import random

import pytest

from rowbit.operations.copy import copy_row
from rowbit.sequencer import LANES

pytestmark = pytest.mark.hardware


def row_words(sequencer):
    return LANES * sequencer.dram.columns // sequencer.dram.burst_length


def test_copy_row_overwrites_destination_with_source(board, sequencer):
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    dram, bus, words = sequencer.dram, board.bus, row_words(sequencer)
    for _ in range(8):
        # An even row and the next one: same subarray for any even-row-aligned subarray layout.
        bank, source = rng.randrange(dram.banks), 2 * rng.randrange(dram.rows // 2)
        destination = source + 1
        source_data = [rng.getrandbits(32) for _ in range(words)]
        bus.write(sequencer.controller_address(bank, source), source_data)
        bus.write(sequencer.controller_address(bank, destination), [rng.getrandbits(32) for _ in range(words)])
        copy_row(sequencer, bank, source, destination)
        where = f"seed {seed}, bank {bank}, rows {source} -> {destination}"
        assert bus.read(sequencer.controller_address(bank, destination), length=words) == source_data, where
        assert bus.read(sequencer.controller_address(bank, source), length=words) == source_data, where
