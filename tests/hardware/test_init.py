import random

import pytest

from rowbit.characterize.subarrays import blocks_inside_subarrays, known_starts
from rowbit.operations.copy import init_rows
from rowbit.sequencer import LANES

pytestmark = pytest.mark.hardware

BLOCK_ROWS = 64


@pytest.mark.parametrize("pattern_word", [0x00000000, 0xFFFFFFFF], ids=["zeros", "ones"])
def test_init_rows_sets_every_row_to_the_pattern(board, sequencer, pattern_word):
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    dram, bus = sequencer.dram, board.bus
    words = LANES * dram.columns // dram.burst_length
    bank = rng.randrange(dram.banks)
    first = rng.choice(blocks_inside_subarrays(known_starts(board.serial, dram)[bank], dram.rows, BLOCK_ROWS))
    pattern_row = first + rng.randrange(BLOCK_ROWS)
    rows = [row for row in range(first, first + BLOCK_ROWS) if row != pattern_row]
    pattern = [pattern_word] * words
    bus.write(sequencer.controller_address(bank, pattern_row), pattern)
    for row in rows:
        bus.write(sequencer.controller_address(bank, row), [pattern_word ^ 0xFFFFFFFF] * words)
    init_rows(sequencer, bank, pattern_row, rows)
    where = f"seed {seed}, bank {bank}, pattern row {pattern_row}"
    wrong = [row for row in rows if bus.read(sequencer.controller_address(bank, row), length=words) != pattern]
    assert wrong == [], where
    assert bus.read(sequencer.controller_address(bank, pattern_row), length=words) == pattern, where
