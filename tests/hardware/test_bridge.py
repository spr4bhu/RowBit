import random
import time

import pytest

pytestmark = pytest.mark.hardware

BLOCK_BYTES = 64 * 1024
MIN_BYTES_PER_SECOND = 50_000  # 1 Mbaud gives ~90 KB/s, 115200 ~11 KB/s


def test_scratch_register_round_trip(board):
    scratch = board.bus.regs.ctrl_scratch
    assert scratch.read() == 0x12345678
    for value in [0, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555] + [random.getrandbits(32) for _ in range(50)]:
        scratch.write(value)
        assert scratch.read() == value


def test_large_block_round_trip_is_fast(board):
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    words = [rng.getrandbits(32) for _ in range(BLOCK_BYTES // 4)]
    base = board.bus.mems.main_ram.base + 4 * rng.randrange(1 << 20)
    start = time.time()
    board.bus.write(base, words)
    read_back = board.bus.read(base, length=len(words))
    bytes_per_second = 2 * BLOCK_BYTES / (time.time() - start)
    assert read_back == words, f"seed {seed}"
    assert bytes_per_second > MIN_BYTES_PER_SECOND, f"{bytes_per_second:.0f} B/s"
