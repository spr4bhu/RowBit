# Holds data with refresh off: while the sequencer holds the DRAM bus, the controller's refreshes never reach it.
from rowbit.program import encode_instruction

ALL_ONES = 0xFFFFFFFF
REGION_OFFSET = 64 * 2**20


def retention_flips(sequencer, seconds, size):
    """Writes `size` bytes of ones, keeps refresh off for `seconds`, returns how many bits flipped."""
    bus = sequencer.bus
    region = bus.mems.main_ram.base + REGION_OFFSET
    bus.write(region, [ALL_ONES] * (size // 4))
    cycles = round(seconds * bus.constants.config_clock_frequency)
    sequencer.run([encode_instruction([], wait=cycles)], timeout=seconds + 10)
    return sum(bin(word ^ ALL_ONES).count("1") for word in bus.read(region, length=size // 4))
