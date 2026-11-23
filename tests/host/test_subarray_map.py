from types import SimpleNamespace

from rowbit.characterize.subarrays import SUBARRAY_ROWS, blocks_inside_subarrays, known_starts, save_map

DRAM = SimpleNamespace(banks=2, rows=4 * SUBARRAY_ROWS)
GRID = list(range(SUBARRAY_ROWS, DRAM.rows, SUBARRAY_ROWS))


def test_an_unmapped_board_gets_the_plain_grid(tmp_path):
    assert known_starts("never-mapped", DRAM, tmp_path) == [GRID, GRID]


def test_a_mapped_board_gets_its_saved_starts(tmp_path):
    starts = [GRID, sorted(GRID + [100, 102])]
    save_map("board", starts, seed=1, directory=tmp_path)
    assert known_starts("board", DRAM, tmp_path) == starts
    assert known_starts("other-board", DRAM, tmp_path) == [GRID, GRID]


def test_blocks_never_contain_a_start_after_their_first_row():
    starts = GRID + [100, 102]
    blocks = blocks_inside_subarrays(starts, DRAM.rows, 64)
    assert blocks == [first for first in range(0, DRAM.rows, 64) if first != 64]
