import pytest

from rowbit.characterize.retention import retention_flips

pytestmark = pytest.mark.hardware

REGION_SIZE = 256 * 1024


def test_flips_grow_with_time_without_refresh(sequencer):
    flips = {seconds: retention_flips(sequencer, seconds, REGION_SIZE) for seconds in (0, 20, 40)}
    assert flips[0] == 0 <= flips[20] < flips[40], f"flips per seconds without refresh: {flips}"
