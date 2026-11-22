import random

import pytest

pytestmark = pytest.mark.hardware


def test_scratch_register_round_trip(board):
    scratch = board.bus.regs.ctrl_scratch
    assert scratch.read() == 0x12345678
    for value in [0, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555] + [random.getrandbits(32) for _ in range(50)]:
        scratch.write(value)
        assert scratch.read() == value
