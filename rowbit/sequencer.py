import time

from rowbit.dram import DRAM
from rowbit.program import Command, Program, has_command

REGISTERS, PROGRAM, WRITE_DATA, READ_DATA = range(4)
CONTROL, LENGTH, READ_COUNT, WRITE_COUNT = range(4)
BUSY = 0b01
LANES = 4  # 32-bit words per 128-bit data entry
REGION_SHIFT = 14  # word-address bit where the region starts (wb_adr[15:14] in rtl/dram_sequencer.v)


class Sequencer:
    """Runs programs on the DRAM sequencer over the board's bus."""

    def __init__(self, bus):
        self.bus = bus
        self.base = bus.mems.sequencer.base
        self.read_phase = bus.regs.ddrphy_rdphase.read()
        self.write_phase = bus.regs.ddrphy_wrphase.read()
        self.dram = DRAM(bus.constants)

    def program(self):
        """An empty program for this board's PHY phases, closed legally after any last command."""
        close_delay = max(self.dram.write_to_precharge, self.dram.activate_to_precharge)
        return Program(self.read_phase, self.write_phase, close_delay)

    def controller_address(self, bank, row, column=0):
        """Where the controller's ROW_BANK_COL mapping puts this burst on the bus (one entry per burst)."""
        dram = self.dram
        burst_bits = dram.column_bits - (dram.burst_length - 1).bit_length()
        burst = row << (dram.bank_bits + burst_bits) | bank << burst_bits | column // dram.burst_length
        return self.bus.mems.main_ram.base + 4 * LANES * burst

    def address(self, region, word=0):
        return self.base + 4 * ((region << REGION_SHIFT) + word)

    def busy(self):
        return bool(self.bus.read(self.address(REGISTERS, CONTROL)) & BUSY)

    def wait_until_idle(self, timeout=5):
        deadline = time.time() + timeout
        while self.busy():
            if time.time() > deadline:
                raise TimeoutError("sequencer did not finish")

    def run(self, instructions, write_entries=(), timeout=5):
        """Runs the program; write_entries are 128-bit ints, one per WR; returns one 128-bit int per RD."""
        writes = sum(has_command(instruction, Command.WR) for instruction in instructions)
        if len(write_entries) != writes:
            raise ValueError(f"{len(write_entries)} write entries for {writes} writes")
        # Loading while a program runs would overwrite it under the running program.
        if self.busy():
            raise RuntimeError("sequencer is still running a program")
        self.bus.write(self.address(PROGRAM), [word for instruction in instructions for word in instruction])
        if write_entries:
            self.bus.write(self.address(WRITE_DATA), [entry >> (32 * lane) & 0xFFFFFFFF
                                                     for entry in write_entries for lane in range(LANES)])
        self.bus.write(self.address(REGISTERS, LENGTH), len(instructions))
        self.bus.write(self.address(REGISTERS, CONTROL), 1)
        self.wait_until_idle(timeout)
        count = self.bus.read(self.address(REGISTERS, READ_COUNT))
        if not count:
            return []
        words = self.bus.read(self.address(READ_DATA), length=LANES * count)
        return [sum(words[LANES * entry + lane] << (32 * lane) for lane in range(LANES)) for entry in range(count)]
