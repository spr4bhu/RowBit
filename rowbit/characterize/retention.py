# Holds data with refresh off: while the sequencer holds the DRAM bus, the controller's refreshes never reach it.
from rowbit.program import encode_instruction

ALL_ONES = 0xFFFFFFFF


def retention_flips(sequencer, seconds, size):
    """Writes `size` bytes of ones in the middle of DRAM, keeps refresh off for `seconds`, returns flipped bits."""
    bus = sequencer.bus
    main_ram = bus.mems.main_ram
    if size > main_ram.size // 2:
        raise ValueError(f"{size} bytes is over half of DRAM")
    region = main_ram.base + main_ram.size // 2
    bus.write(region, [ALL_ONES] * (size // 4))
    cycles = round(seconds * bus.constants.config_clock_frequency)
    sequencer.run([encode_instruction([], wait=cycles)], timeout=seconds + 10)
    return sum(bin(word ^ ALL_ONES).count("1") for word in bus.read(region, length=size // 4))
