import random

import pytest

from rowbit.characterize.activation_latency import SPEC_ACTIVATE_TO_READ, bit_errors, read_bursts, write_bursts

pytestmark = pytest.mark.hardware


def read_errors(sequencer, activate_to_read, count=256):
    """Bit errors reading fresh random bursts (an early read can corrupt the row, so new data every time)."""
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    locations = sorted({(rng.randrange(8), rng.randrange(2**14), 8 * rng.randrange(128)) for _ in range(count)})
    entries = [rng.getrandbits(128) for _ in locations]
    write_bursts(sequencer, locations, entries)
    return seed, bit_errors(read_bursts(sequencer, locations, activate_to_read), entries), 128 * len(entries)


def test_read_one_tck_after_activate_returns_errors(sequencer):
    seed, errors, bits = read_errors(sequencer, 1)
    assert errors > bits // 10, f"seed {seed}: {errors} of {bits} bits wrong"


def test_read_at_spec_activate_to_read_returns_stored_data(sequencer):
    seed, errors, bits = read_errors(sequencer, SPEC_ACTIVATE_TO_READ)
    assert errors == 0, f"seed {seed}: {errors} of {bits} bits wrong"
