import os

import pytest

from rowbit import Board


@pytest.fixture(scope="session")
def board():
    """Programs the SoC, connects, and waits until the BIOS has initialised DRAM."""
    if not os.environ.get("ARTY_UART"):
        pytest.skip("Arty not connected")
    board = Board()
    board.program()
    board.connect()
    board.boot_log = board.read_console("litex> ")
    yield board
    board.close()
