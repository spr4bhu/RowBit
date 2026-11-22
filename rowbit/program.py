from enum import IntEnum

SLOTS = 4  # DRAM clocks per sys clock
WORDS_PER_INSTRUCTION = 4
BANKS = 8
ADDRESS_BITS = 14
PROGRAM_DEPTH = 1024
WRITE_DEPTH = 512  # reads need no limit: one per instruction, and the read RAM holds 2048
PRECHARGE_ALL = 1 << 10  # A10 on PRE
CLOSE_DELAY = 16  # tCK from the last command to the closing PREA; covers WR->PRE (tWR) at DDR3-600


class Command(IntEnum):
    NOP = 0
    ACT = 1
    PRE = 2
    RD = 3
    WR = 4
    REF = 5
    ZQCS = 6


def encode_slot(command, bank=0, address=0):
    if not 0 <= bank < BANKS or not 0 <= address < 2**ADDRESS_BITS:
        raise ValueError(f"bank {bank} or address {address:#x} out of range")
    return int(Command(command)) | (bank << 3) | (address << 6)


def encode_instruction(slots, wait=0):
    """slots: up to 4 (command, bank, address) tuples, one per DRAM clock; wait: idle sys cycles after."""
    if len(slots) > SLOTS or not 0 <= wait < 2**32:
        raise ValueError(f"{len(slots)} slots or wait {wait} out of range")
    bits = 0
    for index, slot in enumerate(slots):
        bits |= encode_slot(*slot) << (24 * index)
    bits |= wait << 96
    return [(bits >> (32 * word)) & 0xFFFFFFFF for word in range(WORDS_PER_INSTRUCTION)]


def has_command(instruction, command):
    """True if any slot of an encoded instruction holds `command`."""
    bits = sum(word << (32 * index) for index, word in enumerate(instruction))
    return any(bits >> (24 * slot) & 0b111 == command for slot in range(SLOTS))


class Program:
    """DDR3 commands on a DRAM-clock timeline, packed into sequencer instructions."""

    def __init__(self, read_phase, write_phase):
        self.data_phase = {Command.RD: read_phase, Command.WR: write_phase}
        self.time = 0  # tCK of the next command
        self.commands = {}

    def wait(self, tck):
        if tck < 0:
            raise ValueError(f"wait {tck} is negative")
        self.time += tck

    def command(self, command, bank=0, address=0):
        """Issues `command` at the cursor; RD/WR move on to the PHY's read/write phase."""
        encode_slot(command, bank, address)
        if command in self.data_phase:
            self.time += (self.data_phase[command] - self.time) % SLOTS
        self.commands[self.time] = (command, bank, address)
        self.time += 1

    def instructions(self):
        """The program as sequencer instructions, closed by a PREA so the controller gets idle banks back."""
        commands = dict(self.commands)
        commands[self.time - 1 + CLOSE_DELAY] = (Command.PRE, 0, PRECHARGE_ALL)
        cycles = sorted({time // SLOTS for time in commands})
        bundles = [[commands.get(cycle * SLOTS + slot, (Command.NOP,)) for slot in range(SLOTS)]
                   for cycle in cycles]
        waits = [after - before - 1 for before, after in zip(cycles, cycles[1:])] + [0]
        writes = sum(any(slot[0] == Command.WR for slot in bundle) for bundle in bundles)
        if len(bundles) > PROGRAM_DEPTH or writes > WRITE_DEPTH:
            raise ValueError(f"{len(bundles)} instructions or {writes} writes over the limit")
        return [encode_instruction(bundle, wait) for bundle, wait in zip(bundles, waits)]
