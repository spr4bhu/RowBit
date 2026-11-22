import random

import pytest

pytestmark = pytest.mark.hardware


def test_bios_calibrated_dram(board):
    assert "Memtest OK" in board.boot_log
    assert "Memory initialization failed" not in board.boot_log


def test_random_words_read_back(board):
    main_ram = board.bus.mems.main_ram
    seed = random.randrange(2**32)  # new each run, since DRAM keeps old runs' data
    rng = random.Random(seed)
    words = {main_ram.base + 4 * rng.randrange(main_ram.size // 4): rng.getrandbits(32) for _ in range(2000)}
    for address, value in words.items():
        board.bus.write(address, value)
    wrong = [hex(a) for a, v in words.items() if board.bus.read(a) != v]
    assert wrong == [], f"seed {seed}"
