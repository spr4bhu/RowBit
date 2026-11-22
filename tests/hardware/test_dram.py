import random

import pytest

pytestmark = pytest.mark.hardware

DRAM_SIZE = 256 * 1024 * 1024


def test_bios_calibrated_dram(board):
    assert "Memtest OK" in board.boot_log
    assert "Memory initialization failed" not in board.boot_log


def test_random_words_read_back(board):
    base = board.bus.mems.main_ram.base
    rng = random.Random(1)
    words = {base + 4 * rng.randrange(DRAM_SIZE // 4): rng.getrandbits(32) for _ in range(2000)}
    for address, value in words.items():
        board.bus.write(address, value)
    wrong = [hex(a) for a, v in words.items() if board.bus.read(a) != v]
    assert wrong == []
